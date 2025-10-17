import frappe
from frappe.utils import get_datetime, now_datetime, add_to_date
from zkbiocloud.utils.zkteco_import_log import import_zkteco_logs_to_checkins


@frappe.whitelist()
def zkteco_hourly_import_logs():
    try:
        servers = frappe.get_all("ZKTeco Servers", filters={"disabled": 0}, fields=["name", "last_successful_sync"])
        if not servers:
            frappe.log_error("No active servers found", "ZKTeco Scheduler")
            return

        for server in servers:
            server_doc = frappe.get_doc("ZKTeco Servers", server.name)

            # 🕓 Determine start and end time dynamically
            to_date = now_datetime()
            from_date = (
                get_datetime(server_doc.last_successful_sync)
                if server_doc.last_successful_sync
                else add_to_date(to_date, hours=-1)
            )

            frappe.logger().info(f"Fetching ZKTeco logs for {server_doc.name} from {from_date} to {to_date}")

            # Enqueue job for this server
            frappe.enqueue(
                "zkbiocloud.utils.zkteco_import_log.import_zkteco_logs_to_checkins",
                start_date=from_date,
                end_date=to_date,
                server_id=server_doc.name,
                queue="long",
                timeout=1800,
            )

    except Exception:
        frappe.log_error("ZKTeco Scheduler Fatal Error", frappe.get_traceback())
