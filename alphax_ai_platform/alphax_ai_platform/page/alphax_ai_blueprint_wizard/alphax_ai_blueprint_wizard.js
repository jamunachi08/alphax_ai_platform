
frappe.pages['alphax-ai-blueprint-wizard'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('AlphaX Blueprint Wizard'),
    single_column: true
  });

  const $root = $(wrapper).find('.layout-main-section');
  $root.html(`
    <div class="alphax-wiz">
      <div class="alphax-wiz-steps">
        <span class="step active" data-step="1">1. Target</span>
        <span class="step" data-step="2">2. Schema</span>
        <span class="step" data-step="3">3. Mapping</span>
        <span class="step" data-step="4">4. Test</span>
        <span class="step" data-step="5">5. Publish</span>
      </div>

      <div class="alphax-wiz-card">
        <div class="row">
          <div class="col-md-6">
            <label class="control-label">${__('Blueprint Name')}</label>
            <input class="form-control" id="bp_name" placeholder="e.g. Purchase Order Intake (Template)">
          </div>
          <div class="col-md-6">
            <label class="control-label">${__('Target DocType')}</label>
            <input class="form-control" id="bp_doctype" placeholder="Purchase Order / Employee / any DocType">
            <div class="help">${__('Tip: start with Purchase Order or Employee templates, then duplicate and customize.')}</div>
          </div>
        </div>

        <hr/>

        <div class="row">
          <div class="col-md-4">
            <label class="control-label">${__('Default OCR Engine')}</label>
            <select class="form-control" id="bp_ocr">
              <option value="Azure">Azure (Option A)</option>
              <option value="On-Prem" selected>On-Prem (Option B)</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="control-label">${__('Allow User Override')}</label>
            <select class="form-control" id="bp_override">
              <option value="1" selected>${__('Yes')}</option>
              <option value="0">${__('No')}</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="control-label">${__('Language Hint')}</label>
            <select class="form-control" id="bp_lang">
              <option value="auto" selected>auto</option>
              <option value="en">en</option>
              <option value="ar">ar</option>
            </select>
          </div>
        </div>

        <div class="mt-3">
          <button class="btn btn-primary" id="load_fields">${__('Load DocType Fields')}</button>
          <button class="btn btn-default" id="load_templates">${__('Load Templates')}</button>
        </div>

        <div class="mt-4">
          <h4>${__('Schema Fields')}</h4>
          <p class="text-muted">${__('Select the fields you want to extract from the uploaded document. This is Schema-first extraction.')}</p>
          <div id="fields_box" class="alphax-fields"></div>
        </div>

        <div class="mt-4">
          <h4>${__('Save Blueprint')}</h4>
          <button class="btn btn-success" id="save_bp">${__('Save')}</button>
          <span class="text-muted" id="save_status"></span>
        </div>

        <div class="mt-4">
          <h4>${__('Test Ingestion')}</h4>
          <p class="text-muted">${__('Upload a file (PDF/Image/Excel) and create a Draft document using this blueprint. Draft-only by design.')}</p>
          <div class="row">
            <div class="col-md-8">
              <input class="form-control" id="test_file_url" placeholder="/files/yourfile.pdf">
            </div>
            <div class="col-md-4">
              <button class="btn btn-primary" id="run_test">${__('Run Test')}</button>
            </div>
          </div>
          <pre class="mt-3" id="test_out" style="white-space:pre-wrap;"></pre>
        </div>

      </div>
    </div>
  `);

  function render_field_picker(fields) {
    const $box = $root.find('#fields_box');
    $box.empty();
    (fields || []).forEach(f => {
      const key = f.fieldname || '';
      const label = frappe.utils.escape_html(f.label || key);
      const ft = frappe.utils.escape_html(f.fieldtype || '');
      const row = $(`
        <div class="alphax-field-row">
          <label>
            <input type="checkbox" class="alphax-field-check" data-fieldname="${key}" data-label="${label}" data-fieldtype="${ft}">
            <span class="alphax-field-label">${label}</span>
          </label>
          <span class="badge badge-light">${ft}</span>
          <span class="text-muted small">${key}</span>
        </div>
      `);
      $box.append(row);
    });
  }

  async function call(method, args) {
    const r = await frappe.call({ method, args });
    return r.message;
  }

  $root.on('click', '#load_fields', async () => {
    const dt = ($root.find('#bp_doctype').val() || '').trim();
    if (!dt) return frappe.msgprint(__('Enter a Target DocType'));
    const msg = await call('alphax_ai_platform.alphax_ai.api.blueprints.get_doctype_fields', { target_doctype: dt });
    render_field_picker(msg.fields || []);
  });

  $root.on('click', '#load_templates', async () => {
    const msg = await call('alphax_ai_platform.alphax_ai.api.blueprints.list_templates', {});
    const names = (msg.templates || []).map(x => x.name);
    if (!names.length) return frappe.msgprint(__('No templates found'));
    const d = new frappe.ui.Dialog({
      title: __('Select Template'),
      fields: [{fieldtype:'Select', fieldname:'tmpl', label:__('Template'), options:names.join('\n'), reqd:1}],
      primary_action_label: __('Load'),
      primary_action: async () => {
        const t = d.get_value('tmpl');
        const bp = await call('alphax_ai_platform.alphax_ai.api.blueprints.get_blueprint', { name: t });
        $root.find('#bp_name').val(bp.blueprint_name || t);
        $root.find('#bp_doctype').val(bp.target_doctype || '');
        $root.find('#bp_ocr').val(bp.default_ocr_engine || 'On-Prem');
        $root.find('#bp_override').val(String(bp.allow_user_override ? 1 : 0));
        $root.find('#bp_lang').val(bp.language_hint || 'auto');
        render_field_picker(bp._doctype_fields || []);
        // preselect
        setTimeout(() => {
          (bp.schema_fields || []).forEach(sf => {
            $root.find(`.alphax-field-check[data-fieldname="${sf.maps_to || ''}"]`).prop('checked', true);
          });
        }, 50);
        d.hide();
      }
    });
    d.show();
  });

  $root.on('click', '#save_bp', async () => {
    const blueprint_name = ($root.find('#bp_name').val() || '').trim();
    const target_doctype = ($root.find('#bp_doctype').val() || '').trim();
    if (!blueprint_name || !target_doctype) return frappe.msgprint(__('Blueprint Name and Target DocType are required'));

    const schema_fields = [];
    $root.find('.alphax-field-check:checked').each(function() {
      const $c = $(this);
      const fieldname = $c.data('fieldname');
      const label = $c.data('label');
      const fieldtype = $c.data('fieldtype');
      schema_fields.push({
        field_key: fieldname,
        label: label,
        data_type: (fieldtype === 'Date' ? 'Date' : 'String'),
        required: 0,
        maps_to: fieldname
      });
    });

    const payload = {
      blueprint_name,
      target_doctype,
      is_template: 0,
      default_ocr_engine: $root.find('#bp_ocr').val(),
      allow_user_override: cint($root.find('#bp_override').val()),
      language_hint: $root.find('#bp_lang').val(),
      extraction_mode: 'Schema-first',
      schema_fields
    };

    $root.find('#save_status').text(__('Saving...'));
    const msg = await call('alphax_ai_platform.alphax_ai.api.blueprints.save_blueprint', { data: payload });
    $root.find('#save_status').text(__('Saved: ') + msg.name);
  });

  $root.on('click', '#run_test', async () => {
    const file_url = ($root.find('#test_file_url').val() || '').trim();
    const blueprint_name = ($root.find('#bp_name').val() || '').trim();
    if (!file_url) return frappe.msgprint(__('Enter a file URL like /files/xxx.pdf'));
    if (!blueprint_name) return frappe.msgprint(__('Save the blueprint first (or load a template)'));

    $root.find('#test_out').text(__('Running...'));
    const msg = await call('alphax_ai_platform.alphax_ai.api.blueprints.test_ingest', { file_url, blueprint_name });
    $root.find('#test_out').text(JSON.stringify(msg, null, 2));
  });
};
