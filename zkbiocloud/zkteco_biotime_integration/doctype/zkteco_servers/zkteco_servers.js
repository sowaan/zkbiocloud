frappe.ui.form.on('ZKTeco Servers', {
    refresh(frm) {
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
                    method: "zkbiocloud.api.api.import_zkteco_logs_to_checkins",  // ⚙️ Update path!
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
    }
});
