import flet as ft
import sqlite3
import csv
import os
from datetime import datetime

def main(page: ft.Page):
    # --- 0. 页面基础设置 ---
    page.title = "易计记账本"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0 
    page.resize_on_scroll = True 

    # 全局变量
    current_price = 18.0
    target_record_id = None 

    # --- 1. 数据库初始化 ---
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

    # --- 2. 弹窗逻辑 ---
    def close_dialog(e):
        page.close(dlg_confirm)
        load_data()

    def confirm_toggle(e):
        nonlocal target_record_id
        if target_record_id is not None:
            c = conn.cursor()
            c.execute("SELECT status FROM sales WHERE id=?", (target_record_id,))
            res = c.fetchone()
            if res:
                current = res[0] if res[0] else "未结清"
                new_status = "已结清" if current == "未结清" else "未结清"
                c.execute("UPDATE sales SET status=? WHERE id=?", (new_status, target_record_id))
                conn.commit()
                if txt_query_name.value: query_click(None)
                
        page.close(dlg_confirm)
        load_data()
        page.open(ft.SnackBar(ft.Text("✅ 状态已修改")))

    dlg_confirm = ft.AlertDialog(
        modal=True,
        title=ft.Text("确认修改"),
        content=ft.Text("您确定要切换这条记录的【结清状态】吗？"),
        actions=[
            ft.TextButton("取消", on_click=close_dialog),
            ft.TextButton("确定修改", on_click=confirm_toggle),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def on_row_click(e, record_id):
        nonlocal target_record_id
        target_record_id = record_id 
        page.open(dlg_confirm) 

    # --- 3. 核心功能函数 ---
    def export_click(e):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"易计记账本_{timestamp}.csv"
            android_download_dir = "/storage/emulated/0/Download"
            if os.path.exists(android_download_dir):
                save_path = os.path.join(android_download_dir, filename)
                is_android = True
            else:
                save_path = filename
                is_android = False
            
            c = conn.cursor()
            c.execute("SELECT * FROM sales")
            rows = c.fetchall()
            with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["数据库ID", "顾客", "重量", "单价", "总价", "时间", "状态"])
                writer.writerows(rows)
            msg = f"✅ 导出成功！\n请去 Download 文件夹查看" if is_android else f"✅ 导出成功！"
            page.open(ft.SnackBar(ft.Text(msg), open=True))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"❌ 错误: {str(ex)}"), open=True))

    def query_click(e):
        search_txt = txt_query_name.value.strip()
        if not search_txt:
            page.open(ft.SnackBar(ft.Text("❌ 请先输入要查的顾客姓名")))
            return
            
        c = conn.cursor()
        c.execute("SELECT * FROM sales WHERE customer_name LIKE ? ORDER BY id DESC", (f'%{search_txt}%',))
        rows = c.fetchall()
        
        query_result_table.rows.clear()
        
        if not rows:
            query_name_display.value = f"结果：无关于“{search_txt}”的记录"
            query_table_container.visible = False
            query_total_row.visible = False 
        else:
            # 查账统计
            sum_weight = sum(row[2] for row in rows)
            sum_money = sum(row[4] for row in rows)
            sum_unpaid = sum(row[4] for row in rows if row[6] != "已结清")
            
            query_sum_weight.value = f"总重: {round(sum_weight, 1)}"
            query_sum_money.value = f"总额: {round(sum_money, 1)}"
            query_sum_unpaid.value = f"欠: {round(sum_unpaid, 1)}"
            query_sum_unpaid.color = "red" if sum_unpaid > 0 else "green"
            query_total_row.visible = True 

            # 填充表格
            all_names_found = list(set([row[1] for row in rows]))
            unique_count = len(all_names_found)
            
            if unique_count == 1:
                real_name = all_names_found[0]
                query_name_display.value = f"姓名：{real_name}"
                query_result_table.columns = [
                    ft.DataColumn(ft.Text("序号")),
                    ft.DataColumn(ft.Text("斤数"), numeric=True),
                    ft.DataColumn(ft.Text("单价"), numeric=True),
                    ft.DataColumn(ft.Text("应付"), numeric=True),
                    ft.DataColumn(ft.Text("状态")),
                ]
                for i, row in enumerate(rows):
                    status = row[6] if row[6] else "未结清"
                    is_paid = (status == "已结清")
                    query_result_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(str(i + 1))), 
                            ft.DataCell(ft.Text(str(row[2]))), 
                            ft.DataCell(ft.Text(str(row[3]))), 
                            ft.DataCell(ft.Text(f"{row[4]}", weight="bold")), 
                            ft.DataCell(ft.Container(content=ft.Text(status, color="white", size=11), bgcolor="green" if is_paid else "red", padding=4, border_radius=4, alignment=ft.alignment.center)),
                        ])
                    )
            else:
                query_name_display.value = f"搜索：{search_txt} ({unique_count}人)"
                query_result_table.columns = [
                    ft.DataColumn(ft.Text("序号")),
                    ft.DataColumn(ft.Text("顾客")),
                    ft.DataColumn(ft.Text("斤数"), numeric=True),
                    ft.DataColumn(ft.Text("单价"), numeric=True),
                    ft.DataColumn(ft.Text("应付"), numeric=True),
                    ft.DataColumn(ft.Text("状态")),
                ]
                for i, row in enumerate(rows):
                    status = row[6] if row[6] else "未结清"
                    is_paid = (status == "已结清")
                    query_result_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(str(i + 1))),
                            ft.DataCell(ft.Text(row[1], weight="bold", color="blue")),
                            ft.DataCell(ft.Text(str(row[2]))), 
                            ft.DataCell(ft.Text(str(row[3]))), 
                            ft.DataCell(ft.Text(f"{row[4]}", weight="bold")), 
                            ft.DataCell(ft.Container(content=ft.Text(status, color="white", size=11), bgcolor="green" if is_paid else "red", padding=4, border_radius=4, alignment=ft.alignment.center)),
                        ])
                    )
            query_table_container.visible = True
        page.update()

    # --- 4. 界面控件 ---
    
    txt_price = ft.TextField(value=str(current_price), label="单价", width=80, keyboard_type=ft.KeyboardType.NUMBER, height=40, content_padding=5, text_size=14)
    txt_name = ft.TextField(label="顾客姓名", expand=True) 
    txt_weight = ft.TextField(label="斤数", width=100, keyboard_type=ft.KeyboardType.NUMBER)
    
    txt_query_name = ft.TextField(hint_text="输入姓名查账", bgcolor="white", height=45, expand=True, border_color="green", text_size=15, content_padding=10)
    query_name_display = ft.Text(value="姓名：", size=18, weight="bold", color="black")
    
    # 底部查账统计控件
    query_sum_weight = ft.Text("0", size=13, weight="bold")
    query_sum_money = ft.Text("0", size=13, weight="bold")
    query_sum_unpaid = ft.Text("0", size=13, weight="bold", color="red")
    
    query_total_row = ft.Container(
        content=ft.Row([query_sum_weight, query_sum_money, query_sum_unpaid], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=5, visible=False
    )

    # 查账表格
    query_result_table = ft.DataTable(
        # 【修复1】删除了 width=...，让它自动收缩
        heading_row_height=30,
        data_row_min_height=30,
        column_spacing=5, # 间距设小，紧凑
        border=ft.border.all(1, "black"),
        horizontal_lines=ft.border.BorderSide(1, "black"),
        heading_text_style=ft.TextStyle(weight="bold", color="black"),
        # 【修复2】删除了 DataColumn 的 width 参数
        columns=[ft.DataColumn(ft.Text("序号"))],
        rows=[],
    )

    query_table_container = ft.Column(
        controls=[ft.Row(controls=[query_result_table], scroll=ft.ScrollMode.ALWAYS)],
        scroll=ft.ScrollMode.ADAPTIVE, height=150, visible=False
    )

    # 主页统计控件
    main_sum_weight = ft.Text("总斤数: 0", weight="bold", size=14)
    main_sum_money = ft.Text("总金额: 0", weight="bold", size=14)
    main_sum_unpaid = ft.Text("总欠款: 0", weight="bold", size=14, color="red")

    main_summary_bar = ft.Container(
        content=ft.Row(
            controls=[main_sum_weight, main_sum_money, main_sum_unpaid],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY 
        ),
        bgcolor="#EEEEEE", 
        padding=10,
        border=ft.border.symmetric(vertical=ft.border.BorderSide(1, "#CCCCCC"))
    )

    # 主表格
    data_table = ft.DataTable(
        # 【修复3】删除了 width=700，防止强行撑大
        column_spacing=5, # 极小间距，紧凑！
        columns=[
            # 【修复4】删除了所有 DataColumn 的 width 参数，解决报错
            ft.DataColumn(ft.Text("顾客")),   
            ft.DataColumn(ft.Text("状态")),   
            ft.DataColumn(ft.Text("斤数"), numeric=True), 
            ft.DataColumn(ft.Text("单价"), numeric=True),
            ft.DataColumn(ft.Text("总价"), numeric=True), 
            ft.DataColumn(ft.Text("删")),
        ],
        rows=[],
        heading_row_height=40,
        data_row_min_height=40,
    )

    # --- 5. 逻辑函数 ---
    def load_data():
        c = conn.cursor()
        c.execute("SELECT * FROM sales ORDER BY id DESC")
        rows = c.fetchall()
        data_table.rows.clear()
        
        # 计算统计
        total_w = sum(row[2] for row in rows)
        total_m = sum(row[4] for row in rows)
        total_u = sum(row[4] for row in rows if row[6] != "已结清")
        
        main_sum_weight.value = f"总重: {round(total_w, 1)}"
        main_sum_money.value = f"总收: {round(total_m, 1)}"
        main_sum_unpaid.value = f"未收: {round(total_u, 1)}"
        main_sum_unpaid.color = "red" if total_u > 0 else "green"

        for row in rows:
            db_id = row[0]
            status = row[6] if row[6] else "未结清"
            is_paid = (status == "已结清")
            
            status_cell = ft.Container(
                content=ft.Text(status, color="white", size=10), 
                bgcolor="green" if is_paid else "red", 
                padding=2, 
                border_radius=3
            )

            data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row[1], size=13)), 
                        ft.DataCell(status_cell),              
                        ft.DataCell(ft.Text(str(row[2]), size=13)), 
                        ft.DataCell(ft.Text(str(row[3]), size=13)), 
                        ft.DataCell(ft.Text(f"{row[4]}", size=13, weight="bold")), 
                        ft.DataCell(ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", icon_size=18, on_click=lambda e, r_id=db_id: delete_data(r_id))),
                    ],
                    on_select_changed=lambda e, r_id=db_id: on_row_click(e, r_id), 
                )
            )
        page.update()

    def add_data(e):
        try:
            name = txt_name.value.strip()
            if not name: return
            weight = float(txt_weight.value)
            price = float(txt_price.value)
            total = round(weight * price, 2)
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            c = conn.cursor()
            c.execute("INSERT INTO sales (customer_name, weight, unit_price, total_price, created_at, status) VALUES (?, ?, ?, ?, ?, ?)", (name, weight, price, total, time_now, "未结清"))
            conn.commit()
            txt_name.value = ""
            txt_weight.value = ""
            txt_name.focus()
            page.open(ft.SnackBar(ft.Text(f"记账成功：{total}元")))
            load_data()
        except ValueError:
            page.open(ft.SnackBar(ft.Text("数字格式错误")))

    def delete_data(record_id):
        c = conn.cursor()
        c.execute("DELETE FROM sales WHERE id=?", (record_id,))
        conn.commit()
        load_data()
        if txt_query_name.value: query_click(None)

    # --- 6. 布局组装 ---
    
    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.RESTAURANT, color="pink", size=24),
            ft.Text("猪肉记账本", size=18, weight="bold"),
            txt_price
        ], alignment="spaceBetween"),
        padding=10,
        bgcolor="red50",
        border=ft.border.only(bottom=ft.border.BorderSide(1, "grey"))
    )

    input_row_container = ft.Container(
        content=ft.Row([txt_name, txt_weight, ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="green", icon_size=45, on_click=add_data)]),
        padding=10
    )

    scroll_hint_text = ft.Container(
        content=ft.Text("← 左右滑动表格查看完整信息 →", size=12, color="grey"),
        alignment=ft.alignment.center, padding=ft.padding.only(top=5, bottom=5), bgcolor="white"
    )

    table_container = ft.Column(
        controls=[
            ft.Row(controls=[data_table], scroll=ft.ScrollMode.ALWAYS)
        ],
        scroll=ft.ScrollMode.ADAPTIVE,
        expand=True
    )

    bottom_query_panel = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.ElevatedButton("📂 导出 Excel", icon=ft.Icons.DOWNLOAD, on_click=export_click, color="white", bgcolor="#4CAF50", width=200),
                alignment=ft.alignment.center, padding=ft.padding.only(bottom=5)
            ),
            ft.Row([
                txt_query_name,
                ft.ElevatedButton("查询", on_click=query_click, bgcolor="#2E7D32", color="white", height=45, width=80)
            ]),
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=query_name_display,
                        padding=ft.padding.only(left=5, top=5, bottom=5),
                        bgcolor="#E8F5E9", 
                        width=float("inf")
                    ),
                    ft.Divider(height=2, color="black"),
                    query_table_container, 
                    ft.Divider(height=2, color="black"),
                    query_total_row, # 查账底部统计
                ], spacing=0),
                
                bgcolor="#E8F5E9", 
                border=ft.border.all(2, "#4CAF50"), 
                border_radius=8,
                padding=10,
                width=float("inf"),
            )
        ], spacing=10),
        padding=15,
        bgcolor="#FAFAFA",
        border=ft.border.only(top=ft.border.BorderSide(1, "#DDDDDD"))
    )

    safe_area_content = ft.SafeArea(
        content=ft.Column(
            controls=[
                header,
                input_row_container,
                scroll_hint_text, 
                table_container, 
                main_summary_bar, # 主页底部统计
                bottom_query_panel
            ],
            spacing=0, expand=True 
        ),
        expand=True 
    )

    page.add(safe_area_content)
    load_data()

ft.app(target=main)


