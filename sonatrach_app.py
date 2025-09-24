import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import calendar
import json
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="نظام متابعة أيام العمل - سوناطراك",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #2E86AB, #A8D5BA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2E86AB;
        border-right: 4px solid #2E86AB;
        padding-right: 10px;
        margin: 1.5rem 0 1rem 0;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .stat-box:hover {
        transform: translateY(-5px);
    }
    .positive {
        color: #28a745;
        font-weight: bold;
        font-size: 1.3rem;
    }
    .negative {
        color: #dc3545;
        font-weight: bold;
        font-size: 1.3rem;
    }
    .day-w { background-color: #2E86AB; color: white; border-radius: 3px; }
    .day-v { background-color: #A8D5BA; color: black; border-radius: 3px; }
    .day-s { background-color: #F9DC5C; color: black; border-radius: 3px; }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    .location-badge {
        background: linear-gradient(45deg, #FF6B6B, #FF8E53);
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
        display: inline-block;
    }
    .period-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2E86AB;
    }
    .initial-setup {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Functions to save/load data
def get_data_path():
    """Get the path for data file that works in EXE and normal mode"""
    if getattr(sys, 'frozen', False):
        # Running as EXE
        return Path(sys.executable).parent / 'sonatrach_data.json'
    else:
        # Running as script
        return Path(__file__).parent / 'sonatrach_data.json'

def save_data():
    """Save data to session state and JSON file"""
    data = {
        'contract_start': st.session_state.contract_start.isoformat() if st.session_state.contract_start else None,
        'initial_balance': st.session_state.initial_balance,
        'work_periods': [(start.isoformat(), end.isoformat(), location) for start, end, location in st.session_state.work_periods],
        'sick_periods': [(start.isoformat(), end.isoformat()) for start, end in st.session_state.sick_periods]
    }
    
    data_path = get_data_path()
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_data():
    """Load data from JSON file"""
    data_path = get_data_path()
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load contract start date
        contract_start = None
        if data.get('contract_start'):
            contract_start = datetime.date.fromisoformat(data['contract_start'])
        
        # Load initial balance
        initial_balance = data.get('initial_balance', 0)
        
        # Load work periods
        work_periods = []
        for period in data.get('work_periods', []):
            if len(period) == 3:  # With location
                start_str, end_str, location = period
                work_periods.append((datetime.date.fromisoformat(start_str), datetime.date.fromisoformat(end_str), location))
            else:  # Old format
                start_str, end_str = period
                work_periods.append((datetime.date.fromisoformat(start_str), datetime.date.fromisoformat(end_str), ""))
        
        # Load sick periods
        sick_periods = []
        for start_str, end_str in data.get('sick_periods', []):
            sick_periods.append((datetime.date.fromisoformat(start_str), datetime.date.fromisoformat(end_str)))
        
        return contract_start, initial_balance, work_periods, sick_periods
    except FileNotFoundError:
        return None, 0, [], []

# Initialize session state with loaded data
if 'contract_start' not in st.session_state:
    contract_start, initial_balance, work_periods, sick_periods = load_data()
    st.session_state.contract_start = contract_start
    st.session_state.initial_balance = initial_balance
    st.session_state.work_periods = work_periods
    st.session_state.sick_periods = sick_periods

def calculate_days():
    """Calculate all days from contract start to today"""
    if not st.session_state.contract_start:
        return {}
    
    today = datetime.date.today()
    all_days = {}
    
    current_date = st.session_state.contract_start
    while current_date <= today:
        all_days[current_date] = {'type': 'V', 'location': ''}
        current_date += timedelta(days=1)
    
    # Mark work days with locations
    for start_date, end_date, location in st.session_state.work_periods:
        current = start_date
        while current <= end_date:
            if current in all_days:
                all_days[current] = {'type': 'W', 'location': location}
            current += timedelta(days=1)
    
    # Mark sick days
    for start_date, end_date in st.session_state.sick_periods:
        current = start_date
        while current <= end_date:
            if current in all_days:
                all_days[current] = {'type': 'S', 'location': ''}
            current += timedelta(days=1)
    
    return all_days

def calculate_statistics(days_dict):
    """Calculate statistics from days dictionary"""
    total_w = sum(1 for day_info in days_dict.values() if day_info['type'] == 'W')
    total_v = sum(1 for day_info in days_dict.values() if day_info['type'] == 'V')
    total_s = sum(1 for day_info in days_dict.values() if day_info['type'] == 'S')
    
    # Calculate balance with initial balance
    balance = st.session_state.initial_balance + (total_w - total_v)
    
    # Calculate by location
    location_stats = {}
    for day_info in days_dict.values():
        if day_info['type'] == 'W' and day_info['location']:
            loc = day_info['location'] or 'غير محدد'
            location_stats[loc] = location_stats.get(loc, 0) + 1
    
    return total_w, total_v, total_s, balance, location_stats

def display_calendar(days_dict, year, month):
    """Display monthly calendar with colored days"""
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    st.markdown(f"<div class='sub-header'>🗓️ تقويم {month_name} {year}</div>", unsafe_allow_html=True)
    
    # Create HTML calendar
    html_cal = f"""
    <div style='border: 1px solid #e0e0e0; border-radius: 15px; padding: 1rem; background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'>
    <table style='width: 100%; border-collapse: collapse; text-align: center; font-family: Arial, sans-serif;'>
        <tr style='background: linear-gradient(135deg, #2E86AB, #1a5f7a); color: white;'>
            <th style='padding: 0.8rem; border-radius: 8px 0 0 0;'>الأحد</th>
            <th style='padding: 0.8rem;'>الاثنين</th>
            <th style='padding: 0.8rem;'>الثلاثاء</th>
            <th style='padding: 0.8rem;'>الأربعاء</th>
            <th style='padding: 0.8rem;'>الخميس</th>
            <th style='padding: 0.8rem;'>الجمعة</th>
            <th style='padding: 0.8rem; border-radius: 0 8px 0 0;'>السبت</th>
        </tr>
    """
    
    for week in cal:
        html_cal += "<tr style='height: 60px;'>"
        for day in week:
            if day == 0:
                html_cal += "<td style='padding: 0.5rem; background-color: #f8f9fa;'></td>"
            else:
                current_date = datetime.date(year, month, day)
                if current_date in days_dict:
                    day_info = days_dict[current_date]
                    day_type = day_info['type']
                    location = day_info['location']
                    
                    if day_type == 'W':
                        css_class = 'day-w'
                        tooltip = f'يوم عمل - {location}' if location else 'يوم عمل'
                    elif day_type == 'V':
                        css_class = 'day-v'
                        tooltip = 'إجازة'
                    else:  # 'S'
                        css_class = 'day-s'
                        tooltip = 'عطلة مرضية'
                    
                    html_cal += f"<td style='padding: 0.5rem; position: relative;' class='{css_class}' title='{tooltip}'>"
                    html_cal += f"<div style='font-weight: bold;'>{day}</div>"
                    if location and day_type == 'W':
                        html_cal += f"<div style='font-size: 0.6rem; margin-top: 2px;'>{location[:8]}...</div>"
                    html_cal += "</td>"
                else:
                    html_cal += f"<td style='padding: 0.5rem; background-color: #f8f9fa;'>{day}</td>"
        html_cal += "</tr>"
    
    html_cal += "</table></div>"
    st.markdown(html_cal, unsafe_allow_html=True)

def create_analytics_charts(total_w, total_v, total_s, location_stats):
    """Create analytics charts"""
    # Pie chart for day types
    fig_pie = px.pie(
        values=[total_w, total_v, total_s],
        names=['أيام العمل', 'أيام الإجازة', 'أيام مرضية'],
        title='توزيع أنواع الأيام',
        color=['أيام العمل', 'أيام الإجازة', 'أيام مرضية'],
        color_discrete_map={'أيام العمل': '#2E86AB', 'أيام الإجازة': '#A8D5BA', 'أيام مرضية': '#F9DC5C'}
    )
    fig_pie.update_layout(title_x=0.5, showlegend=True)
    
    # Bar chart for locations
    if location_stats:
        fig_bar = px.bar(
            x=list(location_stats.values()),
            y=list(location_stats.keys()),
            orientation='h',
            title='أيام العمل حسب الورشة',
            labels={'x': 'عدد الأيام', 'y': 'الورشة'},
            color=list(location_stats.values()),
            color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(title_x=0.5)
        
        return fig_pie, fig_bar
    
    return fig_pie, None

# Main app
st.markdown("<h1 class='main-header'>⛽ نظام المتابعة الذكية - سوناطراك</h1>", unsafe_allow_html=True)

# Initial setup if contract start is not set
if not st.session_state.contract_start:
    st.markdown("<div class='initial-setup'>"
                "<h2>🎯 إعدادات البداية</h2>"
                "<p>مرحباً! لنبدأ بإعداد حسابك</p>"
                "</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 تاريخ بداية المتابعة")
        st.info("اختر التاريخ الذي تريد أن تبدأ منه متابعة أيام العمل والإجازة")
        contract_start = st.date_input(
            "تاريخ بداية المتابعة",
            datetime.date(2019, 11, 26),
            help="هذا هو التاريخ الذي سنبدأ منه حساب الأيام"
        )
    
    with col2:
        st.subheader("⚖️ الرصيد الابتدائي")
        st.info("إذا كان لديك رصيد سابق (موجب أو سالب)، أدخله هنا")
        initial_balance = st.number_input(
            "الرصيد الابتدائي (أيام)",
            value=0,
            help="موجب إذا كانت الشركة مدينة لك، سالب إذا كنت مديناً للشركة"
        )
        st.write(f"**الرصيد المدخل:** {initial_balance} يوم")
    
    if st.button("💾 حفظ الإعدادات والبدء", type="primary", use_container_width=True):
        st.session_state.contract_start = contract_start
        st.session_state.initial_balance = initial_balance
        save_data()
        st.success("✅ تم حفظ الإعدادات بنجاح!")
        st.rerun()
    
    st.stop()

# Sidebar for input
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'>"
                "<h3>📊 لوحة التحكم</h3>"
                "<p>نظام المتابعة الذكية لأيام العمل</p>"
                "</div>", unsafe_allow_html=True)
    
    # Contract info
    with st.expander("ℹ️ معلومات العقد", expanded=True):
        st.write(f"**تاريخ البداية:** {st.session_state.contract_start}")
        st.write(f"**الرصيد الابتدائي:** {st.session_state.initial_balance} يوم")
        
        if st.button("✏️ تعديل الإعدادات"):
            st.session_state.contract_start = None
            st.rerun()
    
    st.markdown("---")
    
    # Work period input
    with st.expander("➕ إضافة فترة عمل جديدة", expanded=True):
        work_start = st.date_input("📅 تاريخ بداية العمل", datetime.date.today(), key="work_start")
        work_end = st.date_input("📅 تاريخ نهاية العمل", datetime.date.today(), key="work_end")
        work_location = st.text_input("🏗️ مكان العمل (اختياري)", placeholder="مثال: RIG tp210 أو ورشة الصيانة")
        
        if st.button("💾 حفظ فترة العمل", type="primary", use_container_width=True):
            if work_start <= work_end:
                if work_start >= st.session_state.contract_start:
                    st.session_state.work_periods.append((work_start, work_end, work_location))
                    save_data()
                    st.success("✅ تمت إضافة فترة العمل بنجاح")
                    st.rerun()
                else:
                    st.error("❌ تاريخ البداية يجب أن يكون بعد تاريخ بداية العقد")
            else:
                st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
    
    # Sick leave input
    with st.expander("🏥 إضافة عطلة مرضية"):
        sick_start = st.date_input("📅 تاريخ بداية العطلة المرضية", datetime.date.today(), key="sick_start")
        sick_end = st.date_input("📅 تاريخ نهاية العطلة المرضية", datetime.date.today(), key="sick_end")
        
        if st.button("💾 حفظ العطلة المرضية", use_container_width=True):
            if sick_start <= sick_end:
                if sick_start >= st.session_state.contract_start:
                    st.session_state.sick_periods.append((sick_start, sick_end))
                    save_data()
                    st.success("✅ تمت إضافة العطلة المرضية بنجاح")
                    st.rerun()
                else:
                    st.error("❌ تاريخ البداية يجب أن يكون بعد تاريخ بداية العقد")
            else:
                st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية")
    
    st.markdown("---")
    
    # Data management
    with st.expander("⚙️ إدارة البيانات"):
        # Delete specific work period
        if st.session_state.work_periods:
            period_options = [f"من {start} إلى {end} - {location}" if location else f"من {start} إلى {end}" 
                            for start, end, location in st.session_state.work_periods]
            period_to_delete = st.selectbox("اختر فترة عمل للحذف:", range(len(period_options)), 
                                          format_func=lambda x: period_options[x])
            if st.button("🗑️ حذف الفترة المحددة", use_container_width=True):
                del st.session_state.work_periods[period_to_delete]
                save_data()
                st.success("✅ تم حذف فترة العمل")
                st.rerun()
        
        # Export data
        if st.button("📤 تصدير البيانات", use_container_width=True):
            data = {
                'contract_start': st.session_state.contract_start,
                'initial_balance': st.session_state.initial_balance,
                'work_periods': st.session_state.work_periods,
                'sick_periods': st.session_state.sick_periods
            }
            st.download_button(
                label="💾 تحميل ملف النسخ الاحتياطي",
                data=json.dumps(data, default=str, ensure_ascii=False, indent=2),
                file_name=f"sonatrach_backup_{datetime.date.today()}.json",
                mime="application/json",
                use_container_width=True
            )
        
        if st.button("🗑️ حذف جميع البيانات", use_container_width=True):
            st.session_state.work_periods = []
            st.session_state.sick_periods = []
            save_data()
            st.success("✅ تم حذف جميع البيانات")
            st.rerun()

# Main content
# Calculate statistics
days_dict = calculate_days()
total_w, total_v, total_s, balance, location_stats = calculate_statistics(days_dict)

# Statistics cards
st.markdown("<div class='sub-header'>📊 الإحصائيات التفصيلية</div>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class='stat-box'>
        <h3>🛠️ أيام العمل</h3>
        <h2>{total_w}</h2>
        <div style='font-size: 0.9rem; opacity: 0.9;'>منذ {st.session_state.contract_start}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='stat-box'>
        <h3>🏖️ أيام الإجازة</h3>
        <h2>{total_v}</h2>
        <div style='font-size: 0.9rem; opacity: 0.9;'>إجمالي الإجازات</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='stat-box'>
        <h3>🏥 أيام مرضية</h3>
        <h2>{total_s}</h2>
        <div style='font-size: 0.9rem; opacity: 0.9;'>العطل المرضية</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    balance_class = "positive" if balance >= 0 else "negative"
    balance_icon = "📈" if balance >= 0 else "📉"
    balance_text = "مدينة لك" if balance >= 0 else "مدين للشركة"
    balance_value = abs(balance)
    
    # Show initial balance separately
    initial_text = f"(ابتدائي: {st.session_state.initial_balance})" if st.session_state.initial_balance != 0 else ""
    
    st.markdown(f"""
    <div class='stat-box'>
        <h3>⚖️ الرصيد النهائي</h3>
        <h2 class='{balance_class}'>{balance_icon} {balance}</h2>
        <div style='font-size: 0.9rem; opacity: 0.9;'>{balance_text} بـ {balance_value} يوم {initial_text}</div>
    </div>
    """, unsafe_allow_html=True)

# Analytics charts
st.markdown("<div class='sub-header'>📈 التحليلات البيانية</div>", unsafe_allow_html=True)

fig_pie, fig_bar = create_analytics_charts(total_w, total_v, total_s, location_stats)

if fig_bar:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.plotly_chart(fig_pie, use_container_width=True)

# Location statistics
if location_stats:
    st.markdown("<div class='sub-header'>🏗️ إحصائيات الورشات</div>", unsafe_allow_html=True)
    
    loc_cols = st.columns(3)
    locations_list = list(location_stats.items())
    
    for i, (loc, days) in enumerate(locations_list):
        with loc_cols[i % 3]:
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 1rem; border-radius: 10px; text-align: center;'>
                <h4>🔧 {loc or 'غير محدد'}</h4>
                <h3>{days} يوم</h3>
                <div style='font-size: 0.8rem;'>{days/total_w*100:.1f}% من إجمالي العمل</div>
            </div>
            """, unsafe_allow_html=True)

# Periods display
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='sub-header'>📋 سجل فترات العمل</div>", unsafe_allow_html=True)
    
    if st.session_state.work_periods:
        for i, (start, end, location) in enumerate(st.session_state.work_periods, 1):
            days = (end - start).days + 1
            st.markdown(f"""
            <div class='period-card'>
                <div style='display: flex; justify-content: between; align-items: center;'>
                    <h4>الفترة {i}</h4>
                    {f"<span class='location-badge'>{location}</span>" if location else ""}
                </div>
                <p>📅 من <strong>{start}</strong> إلى <strong>{end}</strong></p>
                <p>⏱️ المدة: <strong>{days}</strong> يوم</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📝 لا توجد فترات عمل مسجلة بعد")

with col2:
    st.markdown("<div class='sub-header'>🏥 سجل العطل المرضية</div>", unsafe_allow_html=True)
    
    if st.session_state.sick_periods:
        for i, (start, end) in enumerate(st.session_state.sick_periods, 1):
            days = (end - start).days + 1
            st.markdown(f"""
            <div class='period-card'>
                <h4>عطلة مرضية {i}</h4>
                <p>📅 من <strong>{start}</strong> إلى <strong>{end}</strong></p>
                <p>⏱️ المدة: <strong>{days}</strong> يوم</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🏥 لا توجد عطل مرضية مسجلة")

# Calendar section
st.markdown("---")
st.markdown("<div class='sub-header'>📅 التقويم التفاعلي</div>", unsafe_allow_html=True)

# Month and year selection
today = datetime.date.today()
current_year = today.year
current_month = today.month

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    selected_year = st.selectbox("السنة", range(st.session_state.contract_start.year, current_year + 1), 
                               index=current_year - st.session_state.contract_start.year)
with col2:
    selected_month = st.selectbox("الشهر", range(1, 13), index=current_month - 1)

display_calendar(days_dict, selected_year, selected_month)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #666; padding: 2rem;'>"
            "⛽ تم التطوير بواسطة عمر بن الشيخ 0666011769"
            "</div>", unsafe_allow_html=True)

# Instructions for creating EXE
# with st.expander("🛠️ كيفية تحويل التطبيق إلى ملف EXE"):
#     st.markdown("""
#     ### خطوات تحويل التطبيق إلى ملف تنفيذي (EXE):
#     
#     1. **تثبيت PyInstaller:**
#     ```bash
#     pip install pyinstaller
#     ```
#     
#     2. **حفظ الكود في ملف:** احفظ هذا الكود في ملف باسم `sonatrach_app.py`
#     
#     3. **إنشاء ملف EXE:**
#     ```bash
#     pyinstaller --onefile --name "SonatrachTracker" sonatrach_app.py
#     ```
#     
#     4. **الملف النهائي:** سيكون الملف التنفيذي في مجلد `dist` باسم `SonatrachTracker.exe`
#     
#     5. **ملاحظات مهمة:**
#     - التطبيق سيحفظ البيانات في نفس مجلد الملف التنفيذي
#     - يمكنك نقل الملف التنفيذي إلى أي كمبيوتر والعمل عليه
#     - البيانات ستكون محفوظة حتى إذا نقلت الملف إلى جهاز آخر
#     """)