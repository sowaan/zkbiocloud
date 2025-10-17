frappe.ui.form.on('ZKTeco Servers', {
    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__('Import Data'), function () {

            // ✅ Default date range: last 15 days
            const now = frappe.datetime.now_datetime();
            const from_date = frappe.datetime.add_days(now, -15);

            // Prompt user for filters
            frappe.prompt([
                {
                    label: 'From Date & Time',
                    fieldname: 'from_date',
                    fieldtype: 'Datetime',
                    reqd: 1,
                    default: from_date
                },
                {
                    label: 'To Date & Time',
                    fieldname: 'to_date',
                    fieldtype: 'Datetime',
                    reqd: 1,
                    default: now
                },
                {
                    label: 'Employee',
                    fieldname: 'employee_id',
                    fieldtype: 'Link',
                    options: 'Employee',
                    reqd: 0,
                    description: 'Optional: select to import logs for a single employee only'
                }
            ],
            function (values) {
                frappe.call({
                    method: "zkbiocloud.utils.zkteco_import_log.import_zkteco_logs_to_checkins",  // ⚙️ Update path!
                    args: {
                        start_date: values.from_date,
                        end_date: values.to_date,
                        server_id: frm.doc.name,
                        employee_id: values.employee_id || null
                    },
                    freeze: true,
                    freeze_message: __("Importing attendance data..."),
                    callback: function (r) {
                        if (!r.exc) {
                            const msg = r.message || {};
                            if (msg.result === "success") {
                                frappe.msgprint({
                                    title: __("✅ Import Successful"),
                                    indicator: "green",
                                    message: `
                                        <b>${msg.inserted || 0}</b> records imported<br>
                                        <b>${msg.skipped || 0}</b> skipped<br><br>
                                        <b>Server:</b> ${msg.server_name || frm.doc.name}
                                    `
                                });
                            } else {
                                frappe.msgprint({
                                    title: __("❌ Import Failed"),
                                    indicator: "red",
                                    message: msg.message || __("An unexpected error occurred.")
                                });
                            }
                        }
                    }
                });
            },
            __('Fetch Attendance Logs'),
            __('Run Import')
            );
        }).addClass('btn-primary');
    },
onload_post_render(frm) {
        // ✅ Automatically add default log type mappings if table is empty
        if (frm.is_new() && (!frm.doc.detail_table || frm.doc.detail_table.length === 0)) {

            const default_mappings = [
                {
                    log_type: "IN",
                    expected_values: "in, check-in, check in, punch-in"
                },
                {
                    log_type: "OUT",
                    expected_values: "out, check-out, check out, punch-out"
                }
            ];

            default_mappings.forEach(mapping => {
                frm.add_child("detail_table", mapping);
            });

            frm.refresh_field("detail_table");
            frappe.msgprint({
                title: __("Default Mappings Added"),
                message: __("Default IN/OUT mappings have been added to Log Type Mapping table."),
                indicator: "blue"
            });
        }
    }    
});
