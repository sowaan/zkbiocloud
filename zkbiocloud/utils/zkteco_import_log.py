import frappe
import requests
import json
from frappe.utils import get_datetime, format_datetime, now_datetime


@frappe.whitelist()
def import_zkteco_logs_to_checkins(start_date, end_date, server_id=None, employee_id=None):
    """
    Fetch attendance logs from ZKTeco API and insert into Employee Checkin.
    If no server_id is provided, it will run for all active (disabled=0) ZKTeco Servers.
    """

    try:
        servers = []

        # ✅ CASE 1: Specific server
        if server_id:
            servers = [frappe.get_doc("ZKTeco Servers", server_id)]

        # ✅ CASE 2: All active servers
        else:
            server_list = frappe.get_all("ZKTeco Servers", filters={"disabled": 0}, fields=["name"])
            if not server_list:
                frappe.throw("❌ No active ZKTeco Servers found.")
            servers = [frappe.get_doc("ZKTeco Servers", s.name) for s in server_list]

        total_inserted, total_skipped = 0, 0
        summary = []

        for server in servers:
            frappe.msgprint(f"🔄 Processing server: <b>{server.name}</b>")

            url = _build_api_url(server)
            headers = _build_headers(server)
            payload = _build_payload(start_date, end_date, employee_id)

            logs = _fetch_zkteco_logs(url, headers, payload)
            if not logs:
                frappe.msgprint(f"⚠️ No logs found for server <b>{server.name}</b>")
                continue

            mapping = _get_field_mapping(server)
            log_type_mapping = _get_log_type_mapping(server)

            # ✅ Only create Import Log if enabled
            log_doc = None
            if server.create_logs:
                log_doc = frappe.new_doc("ZKTeco Import Log")
                log_doc.server = server.name
                log_doc.start_date = start_date
                log_doc.end_date = end_date
                log_doc.employee_id = employee_id

            inserted, skipped = _process_logs(logs, mapping, log_type_mapping, log_doc)

            if log_doc:
                log_doc.inserted_count = inserted
                log_doc.skipped_count = skipped
                log_doc.result_status = "Success" if skipped == 0 else "Partial"
                log_doc.insert(ignore_permissions=True)

            server_doc = frappe.get_doc("ZKTeco Servers", server.name)
            server_doc.last_successful_sync = now_datetime()
            server_doc.save(ignore_permissions=True)

            frappe.db.commit()

            total_inserted += inserted
            total_skipped += skipped
            summary.append(f"✅ {server.name}: {inserted} inserted, {skipped} skipped")

        frappe.msgprint(
            f"<b>Import Completed</b><br>"
            f"Total Inserted: {total_inserted}<br>Total Skipped: {total_skipped}<br><br>"
            + "<br>".join(summary)
        )

        return {
            "result": "success",
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
            "details": summary
        }

    except Exception as e:
        frappe.log_error("ZKTeco Import Checkins Error", frappe.get_traceback())
        return {"result": "failed", "message": str(e)}


# ───────────────────────────────
# Helper Functions
# ───────────────────────────────

def _build_api_url(server):
    if str(server.api_url).endswith(str(server.port)):
        return f"{server.api_url}/{server.api_to_call}/"
    return f"{server.api_url}:{server.port}/{server.api_to_call}/"


def _build_headers(server):
    return {"Content-Type": "application/json", "Token": server.token}


def _build_payload(start_date, end_date, employee_id=None):
    """Build the payload for API call, filtered by employee if provided."""
    
    # Convert datetime objects to string if necessary
    if not isinstance(start_date, str):
        start_date = format_datetime(start_date, "yyyy-MM-dd HH:mm:ss")
    if not isinstance(end_date, str):
        end_date = format_datetime(end_date, "yyyy-MM-dd HH:mm:ss")

    payload = {"StartDate": start_date, "EndDate": end_date}

    if employee_id:
        device_id = frappe.db.get_value("Employee", employee_id, "attendance_device_id")
        if not device_id:
            frappe.throw(f"Employee {employee_id} has no attendance_device_id set.")
        payload["BadgeNumber"] = device_id

    return payload



def _fetch_zkteco_logs(url, headers, payload):
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code != 200:
        frappe.throw(f"API request failed: {response.text}")
    return response.json().get("message", [])


def _get_field_mapping(server):
    return {
        "employee_field": server.employee_device_id or "BadgeNumber",
        "time_field": server.time_field_name or "VerifyTime",
        "logtype_field": server.log_type or "Status",
        "device_field": server.device_id or "DeviceSerialNumber",
        "gps_field": server.gps_location or "GpsLocation",
    }


def _get_log_type_mapping(server):
    mapping_table = server.get("log_type_mapping") or []
    custom_mappings = {}
    for row in mapping_table:
        expected_values = [v.strip().lower() for v in (row.expected_values or "").split(",") if v.strip()]
        if expected_values:
            custom_mappings[row.log_type.upper()] = expected_values
    return custom_mappings


def _normalize_log_type(status, log_type_mapping):
    status = (status or "").strip().lower()
    if log_type_mapping:
        for key, expected_list in log_type_mapping.items():
            if any(val in status for val in expected_list):
                return key
    if any(x in status for x in ["in", "check-in", "check in", "punch-in"]):
        return "IN"
    if any(x in status for x in ["out", "check-out", "check out", "punch-out"]):
        return "OUT"
    return None


def _process_logs(logs, mapping, log_type_mapping, import_log_doc=None):
    inserted, skipped = 0, 0

    for log in logs:
        badge_number = log.get(mapping["employee_field"])
        verify_time = log.get(mapping["time_field"])
        status = log.get(mapping["logtype_field"])
        device_sn = log.get(mapping["device_field"])
        gps_location = log.get(mapping["gps_field"])

        def log_skip(reason):
            nonlocal skipped
            skipped += 1
            if import_log_doc:
                import_log_doc.append("log_details", {
                    "badge_number": badge_number,
                    "verify_time": verify_time,
                    "status": status,
                    "reason": reason,
                    "device_id": device_sn,
                    "gps_location": gps_location
                })

        if not badge_number or not verify_time:
            log_skip("Missing badge number or verify time")
            continue

        log_type = _normalize_log_type(status, log_type_mapping)
        if not log_type:
            log_skip(f"Unknown log type for status: {status}")
            continue

        employee = frappe.db.get_value("Employee", {"attendance_device_id": badge_number}, "name")
        if not employee:
            log_skip(f"Employee not found for device_id {badge_number}")
            continue

        punch_datetime = get_datetime(verify_time)
        if frappe.db.exists("Employee Checkin", {"employee": employee, "time": punch_datetime}):
            log_skip("Duplicate check-in record")
            continue

        frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": punch_datetime,
            "log_type": log_type,
            "device_id": device_sn,
            "custom_gps_location": gps_location
        }).insert(ignore_permissions=True)

        inserted += 1

    return inserted, skipped
