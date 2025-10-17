import frappe # type: ignore

def after_install():
    """
    Populate default Log Type Mapping with separate rows for each expected value.
    """
    try:
        # Check if child table already has records
        if frappe.db.count("Log Type Mapping") > 0:
            frappe.logger().info("ℹ️ Log Type Mapping already populated.")
            return

        # Define mappings for IN and OUT
        mappings = {
            "IN": ["Check-In", "In", "IN", "Sign-In", "Entry"],
            "OUT": ["Check-Out", "Out", "OUT", "Sign-Out", "Exit"]
        }

        # Insert each mapping as a separate row
        for log_type, values in mappings.items():
            for val in values:
                frappe.get_doc({
                    "doctype": "Log Type Mapping",
                    "log_type": log_type,
                    "expected_values": val
                }).insert(ignore_permissions=True)

        frappe.db.commit()
        frappe.logger().info("✅ Default Log Type Mapping inserted successfully.")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error populating Log Type Mapping")
