import frappe
import requests
import json
from frappe.utils import get_datetime


@frappe.whitelist()
def import_zkteco_logs_to_checkins(start_date, end_date, server_id=None, employee_id=None):
    """
    Fetch attendance logs from ZKTeco API and insert into Employee Checkin.

    Args:
        start_date (str): e.g. "2025-01-09 13:49:00"
        end_date (str): e.g. "2025-10-08 13:49:00"
        server_id (str, optional): ZKTeco Servers record name.
        employee_id (str, optional): ERPNext Employee ID to fetch specific employee logs.
    """
    try:
        # ✅ 1. Get ZKTeco server settings
        if server_id:
            server = frappe.get_doc("ZKTeco Servers", server_id)
        else:
            server = frappe.get_all("ZKTeco Servers", filters={"disabled": 0}, fields=["name"], limit=1)
            if not server:
                frappe.throw("❌ No active ZKTeco Server found.")
            server = frappe.get_doc("ZKTeco Servers", server[0].name)

        # ✅ 2. Build URL
        if str(server.api_url).endswith(str(server.port)):
            url = f"{server.api_url}/api_gettransctions/"
        else:
            url = f"{server.api_url}:{server.port}/api_gettransctions/"

        # ✅ 3. Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Token": server.token
        }

        # ✅ 4. Prepare payload (if employee_id provided → filter by that device ID)
        payload = {"StartDate": start_date, "EndDate": end_date}

        if employee_id:
            device_id = frappe.db.get_value("Employee", employee_id, "attendance_device_id")
            if not device_id:
                frappe.throw(f"Employee {employee_id} has no attendance_device_id set.")
            payload["BadgeNumber"] = device_id  # assuming ZKTeco API accepts this as filter

        # ✅ 5. Fetch data from API
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            frappe.throw(f"API request failed: {response.text}")

        result = response.json()
        logs = result.get("message", [])
        if not logs:
            frappe.msgprint("⚠️ No attendance logs found for given filters.")
            return {"result": "success", "inserted": 0, "skipped": 0}

        # ✅ 6. Dynamic field mapping
        employee_field = server.employee_device_id or "BadgeNumber"
        time_field = server.time_field_name or "VerifyTime"
        logtype_field = server.log_type or "Status"
        device_field = server.device_id or "DeviceSerialNumber"
        gps_field = server.gps_location or "GpsLocation"

        inserted, skipped = 0, 0

        # ✅ 7. Prepare custom mapping from Log Type Mapping table
        mapping_table = server.get("log_type_mapping") or []
        custom_mappings = {}

        if mapping_table:
            for row in mapping_table:
                expected_values = [v.strip().lower() for v in (row.expected_values or "").split(",") if v.strip()]
                if expected_values:
                    custom_mappings[row.log_type.upper()] = expected_values

        # ✅ 8. Loop through logs
        for log in logs:
            badge_number = log.get(employee_field)
            verify_time = log.get(time_field)
            status = (log.get(logtype_field) or "").strip().lower()
            device_sn = log.get(device_field)
            gps_location = log.get(gps_field)

            if not badge_number or not verify_time:
                skipped += 1
                continue

            # 🔍 Determine log_type
            log_type = None

            if custom_mappings:
                # Use custom mapping
                for key, expected_list in custom_mappings.items():
                    if any(val in status for val in expected_list):
                        log_type = key
                        break
            else:
                # Fallback to default detection
                if any(x in status for x in ["in", "check-in", "check in", "punch-in"]):
                    log_type = "IN"
                elif any(x in status for x in ["out", "check-out", "check out", "punch-out"]):
                    log_type = "OUT"

            if not log_type:
                skipped += 1
                continue

            # 🔍 Find matching employee
            employee = frappe.db.get_value("Employee", {"attendance_device_id": badge_number}, "name")
            if not employee:
                skipped += 1
                continue

            punch_datetime = get_datetime(verify_time)

            # Skip duplicates
            if frappe.db.exists("Employee Checkin", {"employee": employee, "time": punch_datetime}):
                skipped += 1
                continue

            # ✅ Create Employee Checkin
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": employee,
                "time": punch_datetime,
                "log_type": log_type,
                "device_id": device_sn,
                "custom_gps_location": gps_location
            }).insert(ignore_permissions=True)

            inserted += 1

        frappe.db.commit()
        frappe.msgprint(f"✅ Attendance imported successfully! Inserted: {inserted}, Skipped: {skipped}")
        return {"result": "success", "inserted": inserted, "skipped": skipped}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "ZKTeco Import Checkins Error")
        return {"result": "failed", "message": str(e)}
