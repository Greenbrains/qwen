"""
Скрипт для просмотра содержимого базы долгосрочной памяти (memory.db).
"""
import sqlite3
from datetime import datetime

DB_PATH = "data/memory.db"

def view_memory():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем последние 20 записей из таблицы memories, объединяя с пользователями
        query = """
            SELECT m.id, u.alias, m.created_at, m.content, m.kind
            FROM memories m
            JOIN users u ON u.id = m.user_id
            ORDER BY m.created_at DESC
            LIMIT 20
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if not rows:
            print("📭 База памяти пуста. Пока не сохранено ни одного маркера.")
            return
            
        print(f"📚 Последние записи в памяти ({len(rows)} шт.):\n" + "="*60)
        for row in rows:
            dt = datetime.fromtimestamp(row['created_at']).strftime("%Y-%m-%d %H:%M:%S")
            print(f"👤 Пользователь: {row['alias']}")
            print(f"🕒 Время:      {dt}")
            print(f"🏷 Тип:        {row['kind']}")
            print(f"📝 Содержание:\n   {row['content']}")
            print("-" * 60)
            
        conn.close()
    except sqlite3.OperationalError:
        print(f"❌ База данных не найдена по пути: {DB_PATH}")
        print("   Убедитесь, что вы хотя бы раз успешно завершили диалог с авторизованным пользователем.")

if __name__ == "__main__":
    view_memory()