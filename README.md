### ZKTeco BioTime Integration

# ZKTeco BioTime / ZKTime Bio Cloud Integration for SowaanERP (ERPNext)

> ERPNext app to sync attendance logs from **ZKTeco Bio Cloud** into **ERPNext HRMS** (Frappe v15).  
> Automatic scheduled imports, mapping, log tracking, and failed-record handling.

---


## Features

- Configure **multiple ZKTeco servers** inside ERPNext (URL, port, endpoint, token).
- **Map JSON keys** from ZKTeco responses to ERPNext fields.
- **Map log text values** to IN/OUT attendance types (flexible expected value matching).
- **Scheduled sync** that imports logs and creates HRMS attendance / check-in records.
- **Import logs** with audit: start/end, inserted, skipped, failed records with reasons.
- Friendly UI inside ERPNext to view failed rows and reprocess.

---

## Screenshots

— Server configuration & mapping.
-  <img width="1431" height="746" alt="Screenshot 2025-12-04 at 9 49 34 AM" src="https://github.com/user-attachments/assets/ea62e02b-7c45-48ce-b390-d098a96a5891" />

— Import logs list view.
-  <img width="1431" height="746" alt="Screenshot 2025-12-04 at 9 49 53 AM" src="https://github.com/user-attachments/assets/3ab2e148-646c-48ad-a86b-04ccc3d28bb7" />

— Failed records view.
- <img width="1431" height="746" alt="Screenshot 2025-12-04 at 9 50 02 AM" src="https://github.com/user-attachments/assets/f2575888-b311-4398-a5b4-3afad2f21f5e" />
 

---

## Requirements

- Frappe Framework v15
- ERPNext v15
- Python 3.10+ (match your bench setup)
- Bench-managed site

---

## Installation

```bash
# from frappe-bench/apps (or your apps directory)
cd frappe-bench/apps
bench get-app https://github.com/sowaan/zkbiocloud.git

# install app to your site
cd zkbiocloud
bench setup requirements
bench --site your-site install-app zkbiocloud
bench migrate
bench clear-cache
```

## Liscense

mit
