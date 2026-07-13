(function bootstrapSelfCheck() {
  function setFatal(message) {
    const status = document.getElementById('status');
    const treeWrap = document.getElementById('treeWrap');
    const treeLoading = document.getElementById('treeLoading');
    const treeLoadingLabel = document.getElementById('treeLoadingLabel');
    if (status) {
      status.textContent = message;
      status.style.color = '#c44536';
    }
    if (treeWrap) {
      treeWrap.textContent = message;
    }
    if (treeLoading) {
      treeLoading.style.display = 'block';
    }
    if (treeLoadingLabel) {
      treeLoadingLabel.textContent = 'Initialization error';
    }
  }

  window.__pvAppStarted = false;
  window.__pvSetFatal = setFatal;

  window.addEventListener('error', function (event) {
    const message = (event && event.message) ? event.message : 'Unknown UI error';
    setFatal('UI initialization error: ' + message);
  });

  window.addEventListener('unhandledrejection', function (event) {
    const reason = event && event.reason ? String(event.reason) : 'Unknown promise rejection';
    setFatal('UI initialization error: ' + reason);
  });

  setTimeout(function () {
    if (!window.__pvAppStarted) {
      setFatal('UI did not initialize. Try hard refresh (Ctrl+Shift+R).');
    }
  }, 2000);
})();

window.__pvAppStarted = true;
try {
  const treeWrap = document.getElementById('treeWrap');
  const treeLoading = document.getElementById('treeLoading');
  const treeProgress = document.getElementById('treeProgress');
  const treeLoadingLabel = document.getElementById('treeLoadingLabel');
  const refreshTreeBtn = document.getElementById('refreshTreeBtn');
  const editorLineNums = document.getElementById('editorLineNums');
  const editorCursorInfo = document.getElementById('editorCursorInfo');
  const gotoCharInput = document.getElementById('gotoCharInput');
  const gotoCharBtn = document.getElementById('gotoCharBtn');
  const editorCursorBar = document.getElementById('editorCursorBar');
  const editor = document.getElementById('editor');
  const editorHighlight = document.getElementById('editorHighlight');
  const commentTitle = document.getElementById('commentTitle');
  const commentNote = document.getElementById('commentNote');
  const currentPath = document.getElementById('currentPath');
  const promptFile = document.getElementById('promptFile');
  const editorVersion = document.getElementById('editorVersion');
  const compareFrom = document.getElementById('compareFrom');
  const compareTo = document.getElementById('compareTo');
  const versionView = document.getElementById('versionView');
  const diffView = document.getElementById('diffView');
  const renderContextBody = document.getElementById('renderContextBody');
  const renderedPrompt = document.getElementById('renderedPrompt');
  const review = document.getElementById('review');
  const templateType = document.getElementById('templateType');
  const applyBaseBtn = document.getElementById('applyBaseBtn');
  const renderBtn = document.getElementById('renderBtn');
  const statusEl = document.getElementById('status');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');
  let selectedTask = null;
  let selectedVersionInfo = [];
  let errorLineNum = null;  // line number (1-based) of current syntax error, or null
  let errorCharOffset = null;
  const expandedTreeNodes = new Set();

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setActiveTab(tabName) {
    tabButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    tabPanes.forEach(pane => {
      pane.classList.toggle('active', pane.id === 'tab-' + tabName);
    });
  }

  tabButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      setActiveTab(btn.dataset.tab);
    });
  });

  function populateEditorVersionSelector(task, selectedVersion = '') {
    editorVersion.innerHTML = '<option value="">version</option>';
    if (!task || !task.versions || !task.versions.length) {
      editorVersion.value = '';
      return;
    }

    for (const version of task.versions) {
      const opt = document.createElement('option');
      opt.value = version;
      opt.textContent = version;
      editorVersion.appendChild(opt);
    }

    const defaultVersion = selectedVersion || task.versions[0];
    if (task.versions.includes(defaultVersion)) {
      editorVersion.value = defaultVersion;
    } else {
      editorVersion.value = task.versions[0];
    }
  }

  function updateEditorCursorBar() {
    if (!editorCursorBar || !editorCursorInfo) return;
    const pos = editor.selectionStart;
    const before = editor.value.substring(0, pos);
    const lines = before.split('\n');
    const ln = lines.length;
    const col = lines[lines.length - 1].length + 1;
    const charNum = pos;
    const atError = errorLineNum !== null && ln === errorLineNum;
    editorCursorInfo.textContent = `Ln ${ln}, Col ${col} | Char ${charNum}`;
    editorCursorBar.classList.toggle('at-error', atError);
  }

  function moveCursorToChar(target, options = {}) {
    const { announce = true } = options;
    const clamped = Math.max(0, Math.min(target, editor.value.length));
    editor.focus();
    editor.setSelectionRange(clamped, clamped);
    updateEditorCursorBar();

    const before = editor.value.substring(0, clamped);
    const lineIndex = before.split('\n').length - 1;
    const lineHeight = parseFloat(getComputedStyle(editor).lineHeight) || 18;
    const topPadding = parseFloat(getComputedStyle(editor).paddingTop) || 0;
    const targetTop = topPadding + lineIndex * lineHeight;
    const visibleTop = editor.scrollTop;
    const visibleBottom = visibleTop + editor.clientHeight - lineHeight;
    if (targetTop < visibleTop || targetTop > visibleBottom) {
      editor.scrollTop = Math.max(0, targetTop - editor.clientHeight / 2);
      if (editorLineNums) editorLineNums.scrollTop = editor.scrollTop;
    }

    if (announce) {
      setStatus(`Moved cursor to char ${clamped}${clamped !== target ? ` (clamped from ${target})` : ''}`);
    }
  }

  function goToChar() {
    if (!gotoCharInput) return;
    const raw = gotoCharInput.value.trim();
    if (raw === '') {
      setStatus('Enter a character offset first', true);
      gotoCharInput.focus();
      return;
    }

    const target = Number.parseInt(raw, 10);
    if (Number.isNaN(target)) {
      setStatus('Character offset must be an integer', true);
      gotoCharInput.focus();
      gotoCharInput.select();
      return;
    }

    moveCursorToChar(target);
  }

  function updateEditorLineNums() {
    if (!editorLineNums) return;
    const lines = editor.value === '' ? [''] : editor.value.split('\n');
    let html = '';
    for (let i = 0; i < lines.length; i++) {
      const n = i + 1;
      if (n === errorLineNum) {
        html += `<div class="ln-row ln-error" title="Syntax error on this line">🔔${n}</div>`;
      } else {
        html += `<div class="ln-row">${n}</div>`;
      }
    }
    editorLineNums.innerHTML = html;
    editorLineNums.scrollTop = editor.scrollTop;
  }

  function setStatus(msg, isError=false) {
    statusEl.textContent = msg;
    statusEl.style.color = isError ? '#c44536' : '#5a6a85';
  }

  function highlightJinja2Syntax() {
    if (!editorHighlight || !editor) return;
    const text = editor.value;
    let highlightHtml = '';
    let lastIdx = 0;

    // Regex patterns for Jinja2 syntax
    const patterns = [
      { regex: /\{\{.*?\}\}/g, className: 'jinja-var' },              // {{ ... }}
      { regex: /\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}/gs, className: 'jinja-block-raw' }, // {% raw %} ... {% endraw %}
      { regex: /\{%-?\s*.*?-?%\}/g, className: 'jinja-block' },       // {% ... %}
      { regex: /\{#.*?#\}/gs, className: 'jinja-comment' }            // {# ... #}
    ];

    // Collect all matches with positions
    const matches = [];
    for (const pattern of patterns) {
      let match;
      while ((match = pattern.regex.exec(text)) !== null) {
        matches.push({
          start: match.index,
          end: match.index + match[0].length,
          className: pattern.className,
          text: match[0]
        });
      }
    }

    // Sort by start position
    matches.sort((a, b) => a.start - b.start);

    // Build highlighted HTML, handling overlaps
    let currentPos = 0;
    for (const match of matches) {
      // Skip overlapping matches
      if (match.start < currentPos) continue;

      // Add plain text before this match
      if (match.start > currentPos) {
        highlightHtml += `<span class="jinja-text">${escapeHtml(text.substring(currentPos, match.start))}</span>`;
      }

      // Add highlighted match
      highlightHtml += `<span class="${match.className}">${escapeHtml(match.text)}</span>`;
      currentPos = match.end;
    }

    // Add remaining text
    if (currentPos < text.length) {
      highlightHtml += `<span class="jinja-text">${escapeHtml(text.substring(currentPos))}</span>`;
    }

    editorHighlight.innerHTML = highlightHtml;
  }

  function syncEditorOverlayScroll() {
    if (editorLineNums) editorLineNums.scrollTop = editor.scrollTop;
    if (editorHighlight) {
      editorHighlight.scrollTop = editor.scrollTop;
      editorHighlight.scrollLeft = editor.scrollLeft;
    }
  }

  function addRenderContextRow(key = '', value = '') {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input class="ctx-key" placeholder="key" value="${escapeHtml(key)}" /></td>
      <td><input class="ctx-value" placeholder="value" value="${escapeHtml(value)}" /></td>
      <td><button class="remove-row-btn" type="button">Remove</button></td>
    `;
    tr.querySelector('.remove-row-btn').onclick = function() {
      tr.remove();
    };
    renderContextBody.appendChild(tr);
  }

  function populateRenderContextFromVariables(variables) {
    const existing = {};
    renderContextBody.querySelectorAll('tr').forEach(row => {
      const keyInput = row.querySelector('.ctx-key');
      const valueInput = row.querySelector('.ctx-value');
      if (!keyInput || !valueInput) {
        return;
      }
      const key = keyInput.value.trim();
      if (key) {
        existing[key] = valueInput.value;
      }
    });

    renderContextBody.innerHTML = '';
    const vars = Array.isArray(variables) ? variables : [];

    if (!vars.length) {
      addRenderContextRow('', '');
      return;
    }

    vars.forEach(v => {
      addRenderContextRow(v, Object.prototype.hasOwnProperty.call(existing, v) ? existing[v] : '');
    });
  }

  // Returns 'extended' | 'base' | 'standalone'
  function classifyTemplate(content) {
    const text = content || '';
    if (/\{%-?\s*extends\s+["'][^"']+["']\s*-?%\}/m.test(text)) return 'extended';
    if (/\{%-?\s*block\s+\w/m.test(text)) return 'base';
    return 'standalone';
  }

  function updateTemplateTypeIndicator(content) {
    const type = classifyTemplate(content);
    const labels = { extended: 'Template: extended', base: 'Template: base', standalone: 'Template: standalone' };
    templateType.textContent = labels[type];
    applyBaseBtn.style.display = type === 'extended' ? 'inline-block' : 'none';
  }

  function extractPlaceholderKeysFromContent(content) {
    const keys = new Set();
    const text = content || '';
    const re = /\{\{\s*([a-zA-Z_][\w.]*)/g;
    let match;
    while ((match = re.exec(text)) !== null) {
      if (match[1]) {
        keys.add(match[1]);
      }
    }
    return Array.from(keys);
  }

  async function resolveRenderContextKeys(path, content, reviewVars) {
    const keys = new Set(Array.isArray(reviewVars) ? reviewVars : []);
    extractPlaceholderKeysFromContent(content).forEach(k => keys.add(k));

    const extendsMatch = /\{\%\s*extends\s+["']([^"']+)["']\s*\%\}/m.exec(content || '');
    if (extendsMatch && extendsMatch[1]) {
      try {
        const parts = path.split('/');
        if (parts.length >= 1) {
          parts[parts.length - 1] = extendsMatch[1];
          const basePath = parts.join('/');
          const baseData = await api('/api/prompt?path=' + encodeURIComponent(basePath));
          extractPlaceholderKeysFromContent(baseData.content).forEach(k => keys.add(k));
          if (baseData.review && Array.isArray(baseData.review.variables)) {
            baseData.review.variables.forEach(k => keys.add(k));
          }
        }
      } catch (_e) {
        // If base prompt can't be loaded, keep keys extracted from current prompt.
      }
    }

    return Array.from(keys).sort();
  }

  function renderVersionsSidebar(versions, activeVersion = '') {
    if (!versions || versions.length === 0) {
      versionView.innerHTML = '<div class="version-highlight">No versions loaded.</div>';
      return;
    }

    versionView.innerHTML = versions.map(v => {
      const activeClass = v.version === activeVersion ? 'active' : '';
      const syntaxClass = v.has_syntax_error ? ' version-card-syntax-error' : '';
      const highlight = v.title || '(no version highlight)';
      const syntaxMarker = v.has_syntax_error
        ? `<span class="version-syntax-bell" title="${escapeHtml(v.syntax_error || 'Syntax error')}">🔔</span>`
        : '';
      const syntaxMessage = v.has_syntax_error
        ? `<div class="version-syntax-text" title="${escapeHtml(v.syntax_error || 'Syntax error')}">${escapeHtml(v.syntax_error || 'Syntax error')}</div>`
        : '';
      return `
        <div class="version-card ${activeClass}${syntaxClass}" data-version="${escapeHtml(v.version)}">
          <div class="version-name">${syntaxMarker}${escapeHtml(v.version)}</div>
          <div class="version-highlight">${escapeHtml(highlight)}</div>
          ${syntaxMessage}
        </div>
      `;
    }).join('');

    versionView.querySelectorAll('.version-card').forEach(card => {
      card.onclick = async function() {
        if (!selectedTask) return;
        const version = card.getAttribute('data-version');
        if (!version) return;
        const promptPath = selectedTask.family_path + '/' + version + '/' + selectedTask.prompt_file;
        await openPrompt(promptPath);
      };
    });
  }

  async function refreshVersionsSidebar(activeVersion = '') {
    if (!selectedTask) {
      versionView.innerHTML = '<div class="version-highlight">Select a task to view versions.</div>';
      return;
    }
    try {
      const data = await api('/api/version_view?family_path=' + encodeURIComponent(selectedTask.family_path) + '&prompt_file=' + encodeURIComponent(selectedTask.prompt_file));
      selectedVersionInfo = data.versions || [];
      renderVersionsSidebar(selectedVersionInfo, activeVersion || editorVersion.value);
    } catch (e) {
      versionView.innerHTML = '<div class="version-highlight">Failed to load versions.</div>';
    }
  }

  async function api(path, opts={}) {
    const res = await fetch(path, opts);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Request failed');
    }
    return data;
  }

  function setTreeLoading(visible, label='', percent=null) {
    treeLoading.style.display = visible ? 'block' : 'none';
    if (label) {
      treeLoadingLabel.textContent = label;
    }
    if (percent === null) {
      treeProgress.removeAttribute('value');
    } else {
      treeProgress.value = Math.max(0, Math.min(100, percent));
    }
  }

  function buildTreeHtml(nodes, parentPath = '', depth = 0) {
    if (!nodes || !Array.isArray(nodes) || nodes.length === 0) {
      return '';
    }
    
    let html = '<ul>';
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      html += '<li>';
      
      if (node.type === 'dir') {
        const safeName = String(node.name || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const nodePath = parentPath ? (parentPath + '/' + String(node.name || '')) : String(node.name || '');
        const safeNodePath = nodePath.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        const hasChildren = node.children && Array.isArray(node.children) && node.children.length > 0;
        const isExpanded = hasChildren && (expandedTreeNodes.has(nodePath) || depth < 1);
        const toggleSymbol = isExpanded ? '▾' : '▸';

        html += '<div class="tree-dir-row">';
        if (hasChildren) {
          html += '<button class="tree-toggle" type="button" data-node-path="' + safeNodePath + '" aria-expanded="' + (isExpanded ? 'true' : 'false') + '" onclick="window.handleTreeDirToggle(event)">' + toggleSymbol + '</button>';
        } else {
          html += '<span class="tree-toggle tree-toggle-empty" aria-hidden="true"></span>';
        }
        html += '<span class="dir tree-dir-label" data-node-path="' + safeNodePath + '" onclick="window.handleTreeDirToggle(event)">📁 ' + safeName + '</span>';
        html += '</div>';

        if (node.children && Array.isArray(node.children) && node.children.length > 0) {
          const childrenClass = isExpanded ? 'tree-children' : 'tree-children collapsed';
          html += '<div class="' + childrenClass + '" data-node-path="' + safeNodePath + '">';
          html += buildTreeHtml(node.children, nodePath, depth + 1);
          html += '</div>';
        }
      } else if (node.type === 'task') {
        const safeName = String(node.name || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const taskDataStr = JSON.stringify(node.data || {}).replace(/"/g, '&quot;');
        const hasSyntaxError = !!(node.data && node.data.has_syntax_error);
        const syntaxTitle = hasSyntaxError
          ? 'Syntax error in: ' + (node.data.syntax_error_versions || []).map(item => `${item.version}: ${item.error}`).join(' | ')
          : '';
        const fileClass = hasSyntaxError ? 'file file-syntax-error' : 'file';
        const marker = hasSyntaxError ? '<span class="tree-syntax-bell" title="' + escapeHtml(syntaxTitle) + '">🔔</span> ' : '';
        html += '<span class="' + fileClass + '" style="cursor:pointer;" data-task-json="' + taskDataStr + '" onclick="window.handleTreeTaskClick(event)">' + marker + '📋 ' + safeName + '</span>';
      }
      
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  function toggleTreeNode(nodePath) {
    if (!nodePath) return;

    const childrenEl = treeWrap.querySelector('.tree-children[data-node-path="' + CSS.escape(nodePath) + '"]');
    if (!childrenEl) return;

    const isCollapsed = childrenEl.classList.toggle('collapsed');
    if (isCollapsed) {
      expandedTreeNodes.delete(nodePath);
    } else {
      expandedTreeNodes.add(nodePath);
    }

    const isExpanded = !isCollapsed;
    const toggles = treeWrap.querySelectorAll('.tree-toggle[data-node-path="' + CSS.escape(nodePath) + '"]');
    toggles.forEach(toggle => {
      toggle.textContent = isExpanded ? '▾' : '▸';
      toggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
    });
  }

  window.handleTreeTaskClick = function(event) {
    try {
      if (!event || !event.target) return;
      const dataStr = event.target.getAttribute('data-task-json');
      if (!dataStr) return;
      const taskData = JSON.parse(dataStr);
      selectTask(taskData);
    } catch (e) {
      console.error('Tree click error:', e);
    }
  };

  window.handleTreeDirToggle = function(event) {
    try {
      if (!event || !event.target) return;
      event.stopPropagation();
      const nodePath = event.target.getAttribute('data-node-path');
      toggleTreeNode(nodePath);
    } catch (e) {
      console.error('Tree toggle error:', e);
    }
  };

  async function renderTasksTree(treeNodes) {
    try {
      console.log('renderTasksTree called');
      if (!treeWrap) {
        throw new Error('treeWrap element not found');
      }
      const html = buildTreeHtml(treeNodes);
      treeWrap.innerHTML = html;
      setTreeLoading(false);
      setStatus('Prompt task hierarchy loaded');
    } catch (e) {
      console.error('renderTasksTree error:', e);
      if (treeWrap) {
        treeWrap.innerHTML = '<div style="color:red;">Render Error: ' + String(e.message || e) + '</div>';
      }
      setTreeLoading(false);
      setStatus('Tree render error', true);
    }
  }

  async function loadTasksTree(options = {}) {
    const forceReload = !!options.forceReload;
    try {
      setTreeLoading(true, forceReload ? 'Refreshing prompt task hierarchy...' : 'Loading prompt task hierarchy...', null);
      const apiPath = forceReload
        ? ('/api/tasks_tree?force_reload=' + Date.now())
        : '/api/tasks_tree';
      const data = await api(apiPath);
      await renderTasksTree(data.tree);
    } catch (e) {
      console.error('loadTasksTree error:', e);
      setTreeLoading(false);
      if (treeWrap) {
        treeWrap.textContent = 'Error: ' + String(e.message || e);
      }
      setStatus('Error loading tree: ' + String(e.message || e), true);
    }
  }

  async function forceReloadPromptLibrary() {
    if (refreshTreeBtn) refreshTreeBtn.disabled = true;
    try {
      setStatus('Refreshing prompt library...');
      await loadTasksTree({ forceReload: true });
      await refreshVersionsSidebar(editorVersion ? editorVersion.value : '');
      setStatus('Prompt library refreshed');
    } catch (e) {
      setStatus('Refresh failed: ' + String(e.message || e), true);
    } finally {
      if (refreshTreeBtn) refreshTreeBtn.disabled = false;
    }
  }

  async function refreshSyntaxIndicators(activeVersion = '') {
    const version = activeVersion || (editorVersion ? editorVersion.value : '');
    const updates = [];
    if (selectedTask) {
      updates.push(refreshVersionsSidebar(version));
    }
    updates.push(loadTasksTree());
    await Promise.all(updates);
  }

  async function selectTask(task) {
    try {
      setStatus('Loading versions for ' + task.display_name + '...');
      selectedTask = task;
      // Populate the family and promptFile fields
      document.getElementById('family').value = task.family_path;
      document.getElementById('promptFile').value = task.prompt_file;
      populateEditorVersionSelector(task);
      
      // Populate version dropdowns
      const compareFromSelect = document.getElementById('compareFrom');
      const compareToSelect = document.getElementById('compareTo');
      
      // Clear and rebuild the dropdowns
      compareFromSelect.innerHTML = '<option value="">from version</option>';
      compareToSelect.innerHTML = '<option value="">to version</option>';
      
      for (const version of task.versions) {
        const optionFrom = document.createElement('option');
        optionFrom.value = version;
        optionFrom.textContent = version;
        compareFromSelect.appendChild(optionFrom);
        
        const optionTo = document.createElement('option');
        optionTo.value = version;
        optionTo.textContent = version;
        compareToSelect.appendChild(optionTo);
      }
      
      // Set default values: from latest, to 2nd latest (or latest if only one)
      if (task.versions.length > 0) {
        compareToSelect.value = task.versions[0];
        if (task.versions.length > 1) {
          compareFromSelect.value = task.versions[1];
        } else {
          compareFromSelect.value = task.versions[0];
        }
      }
      
      await refreshVersionsSidebar(task.versions[0]);
      
      // Load the first (latest) version automatically
      if (task.versions.length > 0) {
        const firstVersion = task.versions[0];
        const promptPath = task.family_path + '/' + firstVersion + '/' + task.prompt_file;
        await openPrompt(promptPath);
      }

      setActiveTab('editor');
      
      setStatus('Selected task: ' + task.display_name);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  function renderVersionGraph(task) {
    // Kept for backward compatibility. The version sidebar now renders version graph/details.
    if (!task) {
      return;
    }
    refreshVersionsSidebar(editorVersion.value);
  }

  window.loadVersionOfTask = async function(familyPath, promptFile, version) {
    try {
      const promptPath = familyPath + '/' + version + '/' + promptFile;
      if (editorVersion) {
        editorVersion.value = version;
      }
      await openPrompt(promptPath);
      setStatus('Loaded ' + version);
    } catch (e) {
      setStatus(e.message, true);
    }
  };

  async function loadTree() {
    // For backward compatibility, this now loads the tasks tree hierarchy
    await loadTasksTree();
  }

  function isBaseTemplate(path, content) {
    // A template is a base template if it defines blocks but does not extend anything.
    // Standalone templates (no blocks, no extends) can be rendered directly.
    return classifyTemplate(content) === 'base';
  }

  async function openPrompt(path) {
    try {
      const data = await api('/api/prompt?path=' + encodeURIComponent(path));
      currentPath.value = data.path;
      editor.value = data.content;
      editor.scrollTop = 0;
      editor.scrollLeft = 0;
      updateEditorLineNums();
      highlightJinja2Syntax();
      syncEditorOverlayScroll();
      commentTitle.value = (data.metadata && data.metadata.title) ? data.metadata.title : '';
      commentNote.value = (data.metadata && data.metadata.note) ? data.metadata.note : '';
      promptFile.value = path.split('/').pop();
      const parts = path.split('/');
      const currentVersion = parts.length >= 2 ? parts[parts.length - 2] : '';
      if (currentVersion && editorVersion && editorVersion.querySelector('option[value="' + currentVersion + '"]')) {
        editorVersion.value = currentVersion;
      }
      updateTemplateTypeIndicator(data.content);
      // Update workspace task name in header
      const taskNameEl = document.getElementById('workspaceTaskName');
      if (taskNameEl) {
        const pathParts = data.path.split('/');
        const fileName = pathParts.pop();
        const taskPath = pathParts.join('/');
        taskNameEl.innerHTML = taskPath
          ? `<span class="workspace-task-path">${taskPath}/</span><span class="workspace-task-file">${fileName}</span>`
          : `<span class="workspace-task-file">${fileName}</span>`;
      }
      await refreshVersionsSidebar(currentVersion);
      const contextKeys = await resolveRenderContextKeys(
        data.path,
        data.content,
        (data.review && data.review.variables) ? data.review.variables : []
      );
      populateRenderContextFromVariables(contextKeys);
      renderedPrompt.innerHTML = '';
      diffView.textContent = '';
      renderReview(data.review);
      
      // Disable "Render Full Prompt" button for base templates (have blocks but no extends)
      const isBase = isBaseTemplate(data.path, data.content);
      if (renderBtn) {
        renderBtn.disabled = isBase;
        renderBtn.title = isBase ? 'Cannot render base templates directly - they must be extended by other templates' : 'Render the full prompt with all variables resolved';
      }
      
      setStatus('Opened ' + data.path);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  function renderReview(r) {
    const varsHtml = (r.variables || []).map(v => `<span class="chip">${v}</span>`).join('');
    review.innerHTML = `
      <div><strong>Syntax:</strong> <span class="${r.syntax_valid ? 'ok' : 'warn'}">${r.syntax_valid ? 'valid' : 'invalid'}</span></div>
      ${r.syntax_error ? `<div class="warn review-error-link" title="Click to jump to the syntax error"><strong>Error:</strong> ${r.syntax_error}</div>` : ''}
      <div><strong>Lines:</strong> ${r.line_count} | <strong>Chars:</strong> ${r.char_count}</div>
      <div><strong>Variables:</strong> ${varsHtml || '<span class="chip">none</span>'}</div>
      <div><strong>Updated:</strong> ${r.last_modified}</div>
    `;
    errorLineNum = null;
    errorCharOffset = null;
    if (!r.syntax_valid && r.syntax_error) {
      const lineMatch = /\bline\s+(\d+)/.exec(r.syntax_error);
      if (lineMatch) {
        errorLineNum = parseInt(lineMatch[1], 10);
      }
      // Match both "at 9047" (old lexer errors) and "char 9047" (new enriched format)
      const charMatch = /(?:\bchar\s+|at\s+)(\d+)/.exec(r.syntax_error);
      if (charMatch) {
        errorCharOffset = parseInt(charMatch[1], 10);
        if (errorLineNum === null) {
          const before = editor.value.substring(0, errorCharOffset);
          errorLineNum = before.split('\n').length;
        }
      }
    }
    const reviewErrorLink = review.querySelector('.review-error-link');
    if (reviewErrorLink) {
      reviewErrorLink.onclick = function() {
        if (errorCharOffset !== null) {
          moveCursorToChar(errorCharOffset, { announce: true });
          return;
        }
        if (errorLineNum !== null) {
          const lines = editor.value.split('\n');
          const target = Math.max(0, lines.slice(0, Math.max(0, errorLineNum - 1)).join('\n').length + (errorLineNum > 1 ? 1 : 0));
          moveCursorToChar(target, { announce: true });
        }
      };
    }
    updateEditorLineNums();
  }

  async function saveCurrent() {
    const path = currentPath.value;
    if (!path) {
      setStatus('Select a prompt first', true);
      return;
    }
    try {
      const data = await api('/api/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ path, content: editor.value })
      });
      renderReview(data.review);
      await refreshSyntaxIndicators(editorVersion ? editorVersion.value : '');
      setStatus('Saved ' + path);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function reviewCurrent() {
    const path = currentPath.value;
    if (!path) {
      setStatus('Select a prompt first', true);
      return;
    }
    try {
      const data = await api('/api/review?path=' + encodeURIComponent(path));
      renderReview(data.review);
      await refreshSyntaxIndicators(editorVersion ? editorVersion.value : '');
      setStatus('Reviewed ' + path);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function createVersion() {
    const family_path = document.getElementById('family').value.trim();
    const source_version = document.getElementById('sourceVersion').value.trim();
    const new_version = document.getElementById('newVersion').value.trim();
    if (!family_path || !new_version) {
      setStatus('family path and new version are required', true);
      return;
    }
    try {
      const data = await api('/api/create_version', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ family_path, source_version, new_version })
      });
      setStatus('Created version at ' + data.created_path);
      await loadTree();
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  function parseRenderContext() {
    const context = {};
    const rows = renderContextBody.querySelectorAll('tr');
    for (const row of rows) {
      const keyInput = row.querySelector('.ctx-key');
      const valueInput = row.querySelector('.ctx-value');
      if (!keyInput || !valueInput) {
        continue;
      }
      const key = keyInput.value.trim();
      const value = valueInput.value;
      if (!key) {
        continue;
      }
      context[key] = value;
    }
    return context;
  }

  function applyHighlightMarkers(text) {
    // The server wraps every {{ expression }} output with \x00HS\x00 ... \x00HE\x00.
    // Build segments, split by newline, then render each line with a line number.
    const OPEN = '\x00HS\x00';
    const CLOSE = '\x00HE\x00';

    // Parse into segments: [{highlight: bool, text: string}]
    const segments = [];
    const parts = text.split(OPEN);
    segments.push({highlight: false, text: parts[0]});
    for (let i = 1; i < parts.length; i++) {
      const closeIdx = parts[i].indexOf(CLOSE);
      if (closeIdx !== -1) {
        if (closeIdx > 0) segments.push({highlight: true, text: parts[i].substring(0, closeIdx)});
        segments.push({highlight: false, text: parts[i].substring(closeIdx + CLOSE.length)});
      } else {
        segments.push({highlight: false, text: OPEN + parts[i]});
      }
    }

    // Convert segments to per-line arrays of HTML fragments
    const lines = [[]];
    for (const seg of segments) {
      const subLines = seg.text.split('\n');
      for (let i = 0; i < subLines.length; i++) {
        if (i > 0) lines.push([]);
        const escaped = escapeHtml(subLines[i]);
        if (escaped.length === 0) continue;
        if (seg.highlight) {
          lines[lines.length - 1].push('<span class="highlighted-value">' + escaped + '</span>');
        } else {
          lines[lines.length - 1].push(escaped);
        }
      }
    }

    return lines.map((frags, i) =>
      `<div class="rendered-line"><span class="ln">${i + 1}</span><span class="lc">${frags.join('')}</span></div>`
    ).join('');
  }

  async function renderFullPrompt() {
    const path = currentPath.value;
    if (!path) {
      setStatus('Select a prompt first', true);
      return;
    }

    let context;
    try {
      context = parseRenderContext();
    } catch (e) {
      setStatus(e.message, true);
      return;
    }

    try {
      const data = await api('/api/render_full', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ path, context })
      });
      // Highlight only actual variable substitutions via server-placed markers
      const highlightedHtml = applyHighlightMarkers(data.rendered_prompt_highlighted);
      renderedPrompt.innerHTML = highlightedHtml;
      setActiveTab('render');
      setStatus('Rendered full prompt for ' + path);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function saveMetadata() {
    const path = currentPath.value;
    if (!path) {
      setStatus('Select a prompt first', true);
      return;
    }
    try {
      await api('/api/save_metadata', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          path,
          title: commentTitle.value.trim(),
          note: commentNote.value
        })
      });
      await openPrompt(path);
      setStatus('Saved title/note for ' + path);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function viewVersions() {
    const familyPath = document.getElementById('family').value.trim();
    const fileName = promptFile.value.trim();
    if (!familyPath || !fileName) {
      setStatus('family path and prompt file are required', true);
      return;
    }
    try {
      await refreshVersionsSidebar(editorVersion.value);
      setStatus('Loaded version view for ' + fileName);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function loadSelectedEditorVersion() {
    if (!selectedTask) {
      setStatus('Select a task first', true);
      return;
    }
    const version = editorVersion.value;
    if (!version) {
      setStatus('Select a version', true);
      return;
    }
    const promptPath = selectedTask.family_path + '/' + version + '/' + selectedTask.prompt_file;
    try {
      await openPrompt(promptPath);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  async function highlightDifference() {
    const familyPath = document.getElementById('family').value.trim();
    const fileName = promptFile.value.trim();
    const fromVersion = compareFrom.value;
    const toVersion = compareTo.value;
    if (!familyPath || !fileName || !fromVersion || !toVersion) {
      setStatus('family path, prompt file, from version, and to version are required', true);
      return;
    }
    try {
      const data = await api('/api/diff_versions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          family_path: familyPath,
          prompt_file: fileName,
          from_version: fromVersion,
          to_version: toVersion
        })
      });
      diffView.innerHTML = data.diff_lines.map(d => {
        const cls = d.type === 'add' ? 'line-add' : (d.type === 'del' ? 'line-del' : 'line-ctx');
        return `<div class="${cls}">${d.prefix} ${d.text}</div>`;
      }).join('');
      setActiveTab('diff');
      setStatus(`Compared ${fromVersion} -> ${toVersion}`);
    } catch (e) {
      setStatus(e.message, true);
    }
  }

  document.getElementById('saveBtn').onclick = saveCurrent;
  document.getElementById('reviewBtn').onclick = reviewCurrent;
  document.getElementById('renderBtn').onclick = renderFullPrompt;
  document.getElementById('saveMetaBtn').onclick = saveMetadata;
  document.getElementById('createVersionBtn').onclick = createVersion;
  document.getElementById('diffBtn').onclick = highlightDifference;
  document.getElementById('applyBaseBtn').onclick = renderFullPrompt;
  document.getElementById('addContextRowBtn').onclick = function() { addRenderContextRow('', ''); };
  if (refreshTreeBtn) refreshTreeBtn.onclick = forceReloadPromptLibrary;
  editorVersion.onchange = loadSelectedEditorVersion;
  if (gotoCharBtn) gotoCharBtn.onclick = goToChar;
  if (gotoCharInput) {
    gotoCharInput.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        goToChar();
      }
    });
  }

  editor.addEventListener('input', () => {
    updateEditorLineNums();
    highlightJinja2Syntax();
  });
  editor.addEventListener('keyup', updateEditorCursorBar);
  editor.addEventListener('mouseup', updateEditorCursorBar);
  editor.addEventListener('selectionchange', updateEditorCursorBar);
  editor.addEventListener('scroll', syncEditorOverlayScroll);
  updateEditorLineNums();
  highlightJinja2Syntax();
  syncEditorOverlayScroll();

  addRenderContextRow('', '');
  versionView.innerHTML = '<div class="version-highlight">Select a task to view versions.</div>';

  loadTree();
} catch (e) {
  if (window.__pvSetFatal) {
    window.__pvSetFatal('UI initialization error: ' + (e && e.message ? e.message : String(e)));
  }
}
