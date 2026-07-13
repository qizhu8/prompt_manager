"""UI HTML generation for prompt visualization."""


def get_ui_html() -> str:
    """Generate the main UI HTML page.
    
    Returns a minimal HTML page that references external CSS and JS files.
    This keeps the Python code clean and allows for easier maintenance of
    styles and scripts.
    
    Returns:
        str: The complete HTML page as a string.
    """
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Prompt Visualization</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header>
    <h1>Prompt Visualization</h1>
  </header>

  <main class="layout">
    <section class="panel">
      <h2 class="panel-title-row">
        <span>Prompt Tasks</span>
        <button id="refreshTreeBtn" class="small-btn" type="button" title="Force reload prompt library">Refresh</button>
      </h2>
      <div id="treeLoading">
        <div id="treeLoadingLabel">Loading prompt tasks...</div>
        <progress id="treeProgress" value="0" max="100"></progress>
      </div>
      <div id="treeWrap">Loading...</div>
    </section>

    <section class="panel panel-main">
      <h2>Workspace</h2>
      <div class="tab-bar">
        <button class="tab-btn active" data-tab="editor">Editor & Review</button>
        <button class="tab-btn" data-tab="render">Rendering Result</button>
        <button class="tab-btn" data-tab="diff">Diff</button>
      </div>

      <div class="workspace-body">
        <div class="tab-content">
        <div class="tab-pane active" id="tab-editor">
          <div class="workspace">
            <div class="toolbar">
              <input id="currentPath" style="min-width:450px;" readonly placeholder="Select a prompt file" />
              <button class="primary" id="saveBtn">Save</button>
              <button id="reviewBtn">Review</button>
              <button id="saveMetaBtn">Save Title/Note</button>
            </div>

            <div class="toolbar">
              <input id="family" placeholder="family path (e.g. autolabeling/accuracy)" style="min-width:320px;" />
              <input id="promptFile" placeholder="prompt file (e.g. adasset_accuracy.jinja2)" style="min-width:280px;" />
              <select id="editorVersion" style="min-width:160px; padding: 4px;">
                <option value="">version</option>
              </select>
              <span id="templateType" class="template-indicator">Template: n/a</span>
              <button id="applyBaseBtn" style="display:none;">Apply On Base Template</button>
              <input id="sourceVersion" placeholder="source version (optional, e.g. v1)" style="min-width:200px;" />
              <input id="newVersion" placeholder="new version (e.g. v2)" style="min-width:160px;" />
              <button id="createVersionBtn">Create Version</button>
            </div>

            <div class="editor-wrap">
              <div id="editorLineNums" class="line-nums" aria-hidden="true"></div>
              <div class="editor-content-wrapper">
                <div id="editorHighlight" class="editor-highlight" aria-hidden="true"></div>
                <textarea id="editor" placeholder="Prompt content" wrap="off" spellcheck="false"></textarea>
              </div>
            </div>
            <div id="editorCursorBar" class="editor-cursor-bar">
              <span id="editorCursorInfo">Ln 1, Col 1 &nbsp;|&nbsp; Char 0</span>
              <span class="editor-cursor-actions">
                <input id="gotoCharInput" type="number" min="0" step="1" placeholder="Go to char" />
                <button id="gotoCharBtn" type="button">Go</button>
              </span>
            </div>

            <div class="toolbar">
              <input id="commentTitle" style="min-width:320px;" placeholder="Version Highlight (one line)" />
            </div>

            <textarea id="commentNote" placeholder="Prompt note (multi-line)"></textarea>
            <div class="meta" id="review"></div>
          </div>
        </div>

        <div class="tab-pane" id="tab-render">
          <div class="workspace">
            <div class="toolbar">
              <button id="addContextRowBtn">Add Context Row</button>
              <button id="renderBtn">Render Full Prompt</button>
            </div>
            <div class="context-table-wrap">
              <table class="context-table">
                <thead>
                  <tr>
                    <th style="width:35%;">Key</th>
                    <th style="width:55%;">Value</th>
                    <th style="width:10%;">Action</th>
                  </tr>
                </thead>
                <tbody id="renderContextBody"></tbody>
              </table>
            </div>
            <div id="renderedPrompt" class="rendered-prompt-view" placeholder="Rendered full prompt (with extends/includes resolved)"></div>
          </div>
        </div>

        <div class="tab-pane" id="tab-diff">
          <div class="workspace">
            <div class="toolbar">
              <select id="compareFrom" style="min-width:170px; padding: 4px;">
                <option value="">from version</option>
              </select>
              <select id="compareTo" style="min-width:170px; padding: 4px;">
                <option value="">to version</option>
              </select>
              <button id="diffBtn">Highlight Difference</button>
            </div>
            <div id="diffView" title="Highlighted differences between versions"></div>
          </div>
        </div>
      </div>

      <aside class="versions-sidebar">
        <h3>Versions & Version Highlight</h3>
        <div id="versionView" class="versions-list" title="Versions and highlights"></div>
      </aside>
      </div>

      <div class="status" id="status">Ready</div>
    </section>
  </main>

  <script src="/static/app.js"></script>
</body>
</html>
"""


# Backward compatibility
HTML_PAGE = get_ui_html()
