import mysql.connector
import os

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="klawiter"
    )
    print("Verbindung zur Datenbank hergestellt")
    
    cursor = db.cursor()
    
    # Ändern Sie den Datentyp für old_text zu LONGBLOB
    cursor.execute("ALTER TABLE zweig_text MODIFY old_text LONGBLOB NOT NULL")
    print("Tabelle zweig_text aktualisiert: old_text ist jetzt LONGBLOB")
    
    # Korrekter Pfad zu den Dateien
    base_path = r"C:\Users\Chrisi\Documents\PROJECTS\szd\klawiter\working"
    
    # Durch alle zt-Dateien iterieren
    for i in range(8):  # 0 bis 7
        file_name = f"zt_0{i}"
        file_path = os.path.join(base_path, file_name)
        
        if not os.path.exists(file_path):
            print(f"Datei nicht gefunden: {file_path}")
            continue
        
        print(f"Importiere Datei: {file_path}")
        
        try:
            with open(file_path, 'rb') as file:
                content = file.read()
                
                # Da wir schon einen Eintrag haben (zt_07), müssen wir hier aufpassen
                # Wir prüfen, ob bereits ein Eintrag mit dieser ID existiert
                cursor.execute("SELECT COUNT(*) FROM zweig_text WHERE old_id = %s", (i+1,))
                result = cursor.fetchone()
                
                if result[0] > 0:
                    # Update bestehenden Eintrag
                    query = "UPDATE zweig_text SET old_text = %s, old_flags = %s WHERE old_id = %s"
                    cursor.execute(query, (content, b'', i+1))
                else:
                    # Neuen Eintrag erstellen
                    query = "INSERT INTO zweig_text (old_id, old_text, old_flags) VALUES (%s, %s, %s)"
                    cursor.execute(query, (i+1, content, b''))
                
                db.commit()
                print(f"Datei {file_name} erfolgreich importiert ({len(content)} Bytes)")
        
        except Exception as e:
            print(f"Fehler beim Importieren von {file_name}: {e}")
    
    # Import abschließen und Datenbank prüfen
    cursor.execute("SELECT COUNT(*) FROM zweig_text")
    result = cursor.fetchone()
    print(f"Anzahl der Einträge in zweig_text nach dem Import: {result[0]}")
    
    cursor.close()
    db.close()
    print("Import abgeschlossen")

except mysql.connector.Error as err:
    print(f"Fehler bei der Datenbankverbindung: {err}")