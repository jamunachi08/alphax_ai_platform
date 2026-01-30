frappe.pages['alphax-ai-assistant'] = {
  on_page_load: function(wrapper) {
    frappe.ui.make_app_page({
      parent: wrapper,
      title: 'AlphaX AI Platform',
      single_column: true
    });

    $(wrapper).find('.layout-main-section').html(`
      <div class="alphax-ai-shell">
        <div class="alphax-ai-header">
          <div>
            <div class="alphax-ai-title">AlphaX AI Assistant</div>
            <div class="alphax-ai-subtitle">Enterprise AI inside ERPNext</div>
          </div>
          <div class="alphax-ai-actions">
            <button class="btn btn-primary btn-sm" id="alphax-ai-new">New Session</button>
          </div>
        </div>

        <div class="alphax-ai-card">
          <div class="alphax-ai-row">
            <input class="form-control" id="alphax-ai-agent" placeholder="Agent Key (e.g., default)" value="default" />
          </div>
          <div class="alphax-ai-row">
            <textarea class="form-control" id="alphax-ai-message" rows="3" placeholder="Ask something..."></textarea>
          </div>
          <div class="alphax-ai-row alphax-ai-row-right">
            <button class="btn btn-secondary" id="alphax-ai-send">Send</button>
          </div>
          <div class="alphax-ai-output" id="alphax-ai-output"></div>
        </div>
      </div>
    `);

    let session_id = null;

    function append(msg, cls) {
      const el = document.getElementById('alphax-ai-output');
      el.insertAdjacentHTML('beforeend', `<div class="alphax-ai-msg ${cls}">${frappe.utils.escape_html(msg)}</div>`);
      el.scrollTop = el.scrollHeight;
    }

    $('#alphax-ai-new').on('click', () => {
      session_id = null;
      $('#alphax-ai-output').empty();
      append('New session started.', 'system');
    });

    $('#alphax-ai-send').on('click', async () => {
      const agent_key = $('#alphax-ai-agent').val() || 'default';
      const message = $('#alphax-ai-message').val();
      if (!message) return;

      append(message, 'user');
      $('#alphax-ai-message').val('');

      const r = await frappe.call('alphax_ai_platform.alphax_ai.api.chat.chat', {
        agent_key,
        message,
        session_id
      });

      session_id = r.message.session_id;
      append(r.message.reply, 'assistant');
    });
  }
};
