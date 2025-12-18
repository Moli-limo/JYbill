import flet as ft
import sqlite3
import csv
import os # 需要导入 os 模块来获取路径
from datetime import datetime

def main(page: ft.Page):
    # --- 0. 页面设置 ---
    page.title = "猪肉记账系统"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"
    page.window_width = 390
    page.window_height = 844
    
    # 允许键盘被遮挡时滚动 (修复手机输入法遮挡问题)
    page.auto_scroll = True 

    current_price = 18.0

    # --- 1. 数据库 (保持不变) ---
    def init_db():
        conn = sqlite3.connect("pork_mobile.db", check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            weight REAL,
            unit_price REAL,
            total_price REAL,
            created_at TEXT,
            status TEXT)''')
        conn.commit()
        return conn

    conn = init_db()

    # --- 2. 【修改】导出功能：直接保存 ---
    def export_click(e):
        try:
            # 1. 生成文件名 (自动带日期)
            filename = f"猪肉账本_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 2. 查询数据
            c = conn.cursor()
            c.execute("SELECT * FROM sales")
            rows = c.fetchall()
            
            # 3. 直接写入当前目录 (手机上通常是脚本所在文件夹)
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["数据库ID", "顾客", "重量", "单价", "总价", "时间", "状态"])
                writer.writerows(rows)
            
            # 4. 获取文件的完整路径，方便用户找
            full_path = os.path.abspath(filename)
            
            # 5. 弹窗提示成功 (SnackBar)
            page.open(ft.SnackBar(ft.Text(f"✅ 导出成功！\n文件在: {full_path}"), open=True))
            
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"❌ 导出出错: {str(ex)}"), open=True))


    # --- 3. 界面控件 (保持不变) ---
    txt_price = ft.TextField(value=str(current_price), label="今日单价", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    txt_name = ft.TextField(label="顾客姓名", expand=True) 
    txt_weight = ft.TextField(label="买入斤数", width=120, keyboard_type=ft.KeyboardType.NUMBER)
    
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("顾客")),
            ft.DataColumn(ft.Text("斤数"), numeric=True),
            ft.DataColumn(ft.Text("总价"), numeric=True),
            ft.DataColumn(ft.Text("状态")),
            ft.DataColumn(ft.Text("操作")),
        ],
        rows=[]
    )

    # --- 4. 业务逻辑 (保持不变) ---
    def load_data():
        c = conn.cursor()
        c.execute("SELECT * FROM sales ORDER BY id DESC")
        rows = c.fetchall()
        data_table.rows.clear()
        
        for row in rows:
            db_id = row[0]
            status = row[6]
            if status is None: status = "未结清"
            is_paid = (status == "已结清")
            
            data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row[1])),
                        ft.DataCell(ft.Text(str(row[2]))),
                        ft.DataCell(ft.Text(f"¥{row[4]}")),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(status, color="white", size=12),
                                bgcolor="green" if is_paid else "red",
                                padding=5, border_radius=5
                            )
                        ),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.DELETE, 
                                icon_color="red", 
                                on_click=lambda e, r_id=db_id: delete_data(r_id)
                            )
                        ),
                    ],
                    on_select_changed=lambda e, r_id=db_id: toggle_status(r_id), 
                )
            )
        page.update()

    def add_data(e):
        try:
            name = txt_name.value
            weight = float(txt_weight.value)
            price = float(txt_price.value)
            total = round(weight * price, 2)
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, weight, unit_price, total_price, created_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                      (name, weight, price, total, time_now, "未结清"))
            conn.commit()
            
            txt_name.value = ""
            txt_weight.value = ""
            txt_name.focus()
            
            page.open(ft.SnackBar(ft.Text(f"记账成功：{total}元")))
            load_data()
        except ValueError:
            page.open(ft.SnackBar(ft.Text("请输入正确的数字！")))

    def delete_data(record_id):
        c = conn.cursor()
        c.execute("DELETE FROM sales WHERE id=?", (record_id,))
        conn.commit()
        load_data()
        page.open(ft.SnackBar(ft.Text("删除成功")))

    def toggle_status(record_id):
        c = conn.cursor()
        c.execute("SELECT status FROM sales WHERE id=?", (record_id,))
        res = c.fetchone()
        if res:
            current_status = res[0] or "未结清"
            new_status = "已结清" if current_status == "未结清" else "未结清"
            c.execute("UPDATE sales SET status=? WHERE id=?", (new_status, record_id))
            conn.commit()
            load_data()

    # --- 5. 界面组装 ---
    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.RESTAURANT, color="pink", size=30),
            ft.Text("猪肉记账本", size=20, weight="bold"),
            txt_price
        ], alignment="spaceBetween"),
        padding=10,
        bgcolor="red50"
    )

    input_row = ft.Row([
        txt_name, 
        txt_weight, 
        ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", icon_size=40, on_click=add_data)
    ])

    bottom_bar = ft.Container(
        content=ft.Row([
            ft.ElevatedButton(
                "📂 导出 Excel/CSV (直接保存)", 
                icon=ft.Icons.DOWNLOAD, 
                on_click=export_click, # 绑定新的导出函数
                color="white",
                bgcolor="green"
            )
        ], alignment="center"),
        padding=10
    )

    page.add(
        header,
        ft.Divider(),
        ft.Container(content=input_row, padding=10),
        ft.Text("点击表格行可切换结清状态", size=12, color="grey"),
        ft.Column([data_table], scroll="auto", expand=True),
        ft.Divider(),
        bottom_bar
    )

    load_data()

ft.app(target=main)