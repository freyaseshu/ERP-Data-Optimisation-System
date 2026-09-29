import pymysql

passwords = [
    '', 'root', 'password', 'Password123!', 'admin', '123456', 
    'mysql', 'root123', 'Password123', 'Password123#', 
    'super-secret-erp-key-2024', 'erp_password', 'erp123', 'Pass1234'
]

for p in passwords:
    try:
        conn = pymysql.connect(host='127.0.0.1', user='root', password=p, port=3306)
        print(f"MATCH FOUND! Root password is: '{p}'")
        conn.close()
        break
    except pymysql.err.OperationalError as e:
        print(f"Tested '{p}': Access denied")
    except Exception as e:
        print(f"Tested '{p}': Error {e}")
