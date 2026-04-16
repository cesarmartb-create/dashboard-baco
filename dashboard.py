import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io, os, json
from datetime import date, datetime

st.set_page_config(
    page_title="Dashboard Grupo Baco",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.metric-card { background: #0f1117; border: 1px solid #1e2130; border-radius: 12px; padding: 1.2rem 1.4rem; }
.metric-label { font-size: 11px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: #6b7280; margin-bottom: 6px; }
.metric-value { font-size: 28px; font-weight: 600; color: #f9fafb; font-family: 'DM Mono', monospace; }
.metric-delta { font-size: 12px; margin-top: 4px; }
.section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #6b7280; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

HIST_DIR = os.path.join(os.path.dirname(__file__), "historial_dashboard")
os.makedirs(HIST_DIR, exist_ok=True)
HIST_INV  = os.path.join(HIST_DIR, "historial_inventario.csv")
HIST_VTA  = os.path.join(HIST_DIR, "historial_ventas.csv")
HIST_COMP = os.path.join(HIST_DIR, "historial_compras.csv")

NOMBRES = {
    'F0006':'Maipú 1','F0024':'Chillán','F0090':'Castro','F0160':'Talagante',
    'F0171':'PAC','F0234':'Metro Franklin','F0287':'Chillán 3','F0313':'Maipú 3',
    'F0383':'Rancagua 8','F0437':'Talagante 2','F0521':'Maipú Chacabuco'
}

def nota_des(v):
    if v<=1.0: return 5
    elif v<=2.0: return 4
    elif v<=3.0: return 3
    elif v<=4.0: return 2
    else: return 1

def nota_cat(v):
    if v>80: return 5
    elif v>75: return 4
    elif v>70: return 3
    elif v>65: return 2
    else: return 1

def nota_color(n):
    return ['','#ef4444','#ef4444','#f59e0b','#3b82f6','#10b981'][n]

def semaforo(n):
    return ['','🔴','🔴','🟡','🔵','🟢'][n]

with st.sidebar:
    st.markdown("### Cargar datos")
    st.caption("Sube los archivos del período a registrar")
    exist_file = st.file_uploader("Existencias (QlickView)", type="xlsx", key="dash_exist")
    des_file   = st.file_uploader("Desabasto (QlickView)",   type="xlsx", key="dash_des")
    vta_file   = st.file_uploader("Ventas (QlickView)",      type="xlsx", key="dash_vta")
    comp_file  = st.file_uploader("Facturación Simi (.xlsx)", type="xlsx", key="dash_comp")
    fecha_carga = st.date_input("Fecha del período", value=date.today())

    if st.button("Guardar período", type="primary"):
        guardado = []

        if exist_file and des_file:
            df_ex = pd.read_excel(exist_file)
            df_ex.columns = [c.strip() for c in df_ex.columns]
            rename = {}
            for c in df_ex.columns:
                cl = c.lower()
                if 'producto' in cl: rename[c]='codigo'
                elif 'unidad' in cl: rename[c]='unidad'
                elif 'vtas' in cl and '30' in cl: rename[c]='vtas30'
                elif 'existencia' in cl: rename[c]='existencias'
                elif 'precio' in cl and 'vta' in cl: rename[c]='precio_vta'
                elif 'valor' in cl and 'inv' in cl: rename[c]='valor_inv'
                elif 'días' in cl or 'dias' in cl: rename[c]='dias_inv'
            df_ex = df_ex.rename(columns=rename)
            df_des = pd.read_excel(des_file)
            df_des.columns = [c.strip() for c in df_des.columns]
            uni_col = next((c for c in df_des.columns if 'unidad' in c.lower()), None)
            vp_col  = next((c for c in df_des.columns if 'valorpond' in c.lower().replace('.','').replace(' ','')), None)
            rows = []
            for local in (df_ex['unidad'].dropna().unique() if 'unidad' in df_ex.columns else []):
                df_loc = df_ex[df_ex['unidad']==local]
                total = len(df_loc)
                con_venta = len(df_loc[df_loc['vtas30']>0]) if 'vtas30' in df_loc.columns else 0
                val_inv = df_loc['valor_inv'].sum() if 'valor_inv' in df_loc.columns else 0
                dias = df_loc['dias_inv'].mean() if 'dias_inv' in df_loc.columns else 0
                des_pct = float(df_des[df_des[uni_col].astype(str).str.strip()==local][vp_col].sum()) if uni_col and vp_col else 0
                rows.append({'fecha':fecha_carga.isoformat(),'local':local,
                    'des_pct':round(des_pct,4),'cat_pct':round(con_venta/total*100,2) if total>0 else 0,
                    'val_inv':round(val_inv,0),'dias_inv':round(dias,1)})
            df_new = pd.DataFrame(rows)
            if os.path.exists(HIST_INV):
                df_old = pd.read_csv(HIST_INV)
                df_old = df_old[df_old['fecha']!=fecha_carga.isoformat()]
                df_new = pd.concat([df_old, df_new], ignore_index=True)
            df_new.to_csv(HIST_INV, index=False)
            guardado.append("inventario")

        if vta_file:
            df_v = pd.read_excel(vta_file)
            df_v.columns = [c.strip() for c in df_v.columns]
            df_v = df_v[df_v['Farmacia'].notna() & df_v['Dia'].notna()].copy()
            df_v['local'] = df_v['Farmacia'].astype(str).str[:5]
            df_v['semana'] = ((df_v['Dia'].astype(float)-1)//7+1).astype(int)
            vta_sem = df_v.groupby(['local','semana']).agg(
                venta=('Importe Acumulado','sum'),
                tickets=('Tickets Acum.','sum'),
                piezas=('Piezas Acumuladas','sum'),
                ticket_prom=('Promedio por Nota','mean')
            ).reset_index()
            vta_sem['fecha'] = fecha_carga.isoformat()
            if os.path.exists(HIST_VTA):
                df_old = pd.read_csv(HIST_VTA)
                df_old = df_old[df_old['fecha']!=fecha_carga.isoformat()]
                vta_sem = pd.concat([df_old, vta_sem], ignore_index=True)
            vta_sem.to_csv(HIST_VTA, index=False)
            guardado.append("ventas")

        if comp_file:
            df_c = pd.read_excel(comp_file)
            df_c.columns = [c.strip() for c in df_c.columns]
            df_c['monto'] = pd.to_numeric(df_c['monto'], errors='coerce').fillna(0)
            comp_sem = df_c.groupby(['Local','Semana','Año','Mes','Categoría']).agg(monto=('Monto','sum')).reset_index()
            comp_sem['fecha'] = fecha_carga.isoformat()
            if os.path.exists(HIST_COMP):
                df_old = pd.read_csv(HIST_COMP)
                df_old = df_old[df_old['fecha']!=fecha_carga.isoformat()]
                comp_sem = pd.concat([df_old, comp_sem], ignore_index=True)
            comp_sem.to_csv(HIST_COMP, index=False)
            guardado.append("compras")

        if guardado:
            st.success(f"Guardado: {', '.join(guardado)}")
            st.rerun()
        else:
            st.warning("Sube al menos un archivo para guardar")

df_inv  = pd.read_csv(HIST_INV)  if os.path.exists(HIST_INV)  else pd.DataFrame()
df_vta  = pd.read_csv(HIST_VTA)  if os.path.exists(HIST_VTA)  else pd.DataFrame()
df_comp = pd.read_csv(HIST_COMP) if os.path.exists(HIST_COMP) else pd.DataFrame()

col_h1, col_h2 = st.columns([3,1])
with col_h1:
    st.markdown("## Dashboard Grupo Baco")
with col_h2:
    if not df_inv.empty:
        st.caption(f"Última actualización: {df_inv['fecha'].max()}")

st.divider()

if df_inv.empty and df_vta.empty and df_comp.empty:
    st.info("Sube archivos desde el sidebar para comenzar.")
    st.stop()

if not df_inv.empty:
    st.markdown('<p class="section-title">KPIs inventario — último período</p>', unsafe_allow_html=True)
    df_ult = df_inv[df_inv['fecha']==df_inv['fecha'].max()].copy()
    df_ult['nota_des'] = df_ult['des_pct'].apply(nota_des)
    df_ult['nota_cat'] = df_ult['cat_pct'].apply(nota_cat)
    prom_des = df_ult['des_pct'].mean()
    prom_cat = df_ult['cat_pct'].mean()
    total_inv = df_ult['val_inv'].sum()

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Desabasto red</div>
            <div class="metric-value" style="color:{nota_color(nota_des(prom_des))}">{prom_des:.2f}%</div>
            <div class="metric-delta" style="color:{nota_color(nota_des(prom_des))}">nota {nota_des(prom_des)} {semaforo(nota_des(prom_des))}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Catálogo vendido red</div>
            <div class="metric-value" style="color:{nota_color(nota_cat(prom_cat))}">{prom_cat:.1f}%</div>
            <div class="metric-delta" style="color:{nota_color(nota_cat(prom_cat))}">nota {nota_cat(prom_cat)} {semaforo(nota_cat(prom_cat))}</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Inventario total</div>
            <div class="metric-value">${total_inv/1e6:.0f}M</div>
            <div class="metric-delta" style="color:#6b7280">{len(df_ult)} locales</div></div>""", unsafe_allow_html=True)
    with c4:
        mejor = df_ult.loc[df_ult['des_pct'].idxmin()]
        peor  = df_ult.loc[df_ult['des_pct'].idxmax()]
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Rango desabasto</div>
            <div class="metric-value" style="font-size:18px;color:#10b981">{mejor['local']} {mejor['des_pct']:.2f}%</div>
            <div class="metric-delta" style="color:#ef4444">peor: {peor['local']} {peor['des_pct']:.2f}%</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    cols_loc = st.columns(11)
    for i, (_, row) in enumerate(df_ult.sort_values('des_pct').iterrows()):
        with cols_loc[i]:
            nd,nc = int(row['nota_des']),int(row['nota_cat'])
            nombre = NOMBRES.get(row['local'], row['local'])
            st.markdown(f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:.6rem .7rem;text-align:center">
                <div style="font-size:10px;color:#64748b">{row['local']}</div>
                <div style="font-size:11px;font-weight:500;color:#0f172a;margin-bottom:4px">{nombre[:10]}</div>
                <div style="font-size:13px;font-weight:600;color:{nota_color(nd)}">{row['des_pct']:.2f}%</div>
                <div style="font-size:10px;color:#64748b">des n{nd}</div>
                <div style="font-size:13px;font-weight:600;color:{nota_color(nc)};margin-top:2px">{row['cat_pct']:.1f}%</div>
                <div style="font-size:10px;color:#64748b">cat n{nc}</div>
            </div>""", unsafe_allow_html=True)

    if len(df_inv['fecha'].unique()) > 1:
        st.markdown("")
        st.markdown('<p class="section-title">Tendencia KPIs inventario</p>', unsafe_allow_html=True)
        df_trend = df_inv.groupby('fecha').agg(des_pct=('des_pct','mean'),cat_pct=('cat_pct','mean')).reset_index().sort_values('fecha')
        fig_trend = make_subplots(specs=[[{"secondary_y":True}]])
        fig_trend.add_trace(go.Scatter(x=df_trend['fecha'],y=df_trend['des_pct'],name='Desabasto %',
            line=dict(color='#3b82f6',width=2),mode='lines+markers'),secondary_y=False)
        fig_trend.add_trace(go.Scatter(x=df_trend['fecha'],y=df_trend['cat_pct'],name='Catálogo %',
            line=dict(color='#10b981',width=2,dash='dot'),mode='lines+markers'),secondary_y=True)
        fig_trend.add_hline(y=2.0,line_dash="dash",line_color="#f59e0b",annotation_text="Meta des. nota 4",secondary_y=False)
        fig_trend.update_layout(height=260,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(248,250,252,0.5)',
            font=dict(color='#334155',size=11),legend=dict(orientation='h',y=1.1),
            margin=dict(t=30,b=20,l=40,r=40),
            xaxis=dict(gridcolor='#e2e8f0'),yaxis=dict(gridcolor='#e2e8f0'))
        st.plotly_chart(fig_trend, use_container_width=True)
    st.divider()

if not df_vta.empty:
    st.markdown('<p class="section-title">Ventas</p>', unsafe_allow_html=True)
    df_v = df_vta.copy()
    for col in ['venta','tickets','ticket_prom','piezas']:
        if col in df_v.columns:
            df_v[col] = pd.to_numeric(df_v[col],errors='coerce').fillna(0)
    df_v_ult = df_v[df_v['fecha']==df_v['fecha'].max()]
    venta_total = df_v_ult['venta'].sum()
    tickets_total = df_v_ult['tickets'].sum()
    ticket_prom = df_v_ult['ticket_prom'].mean()
    piezas_ticket = df_v_ult['piezas'].sum()/tickets_total if tickets_total>0 else 0

    def nota_ticket(v):
        if v>=10501: return 5
        elif v>=9501: return 4
        elif v>=8501: return 3
        elif v>=7501: return 2
        else: return 1

    vc1,vc2,vc3,vc4 = st.columns(4)
    with vc1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Venta total período</div>
            <div class="metric-value">${venta_total/1e6:.1f}M</div></div>""", unsafe_allow_html=True)
    with vc2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Tickets totales</div>
            <div class="metric-value">{int(tickets_total):,}</div></div>""", unsafe_allow_html=True)
    with vc3:
        nt = nota_ticket(ticket_prom)
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Ticket promedio red</div>
            <div class="metric-value" style="color:{nota_color(nt)}">${ticket_prom:,.0f}</div>
            <div class="metric-delta" style="color:{nota_color(nt)}">nota {nt} {semaforo(nt)}</div></div>""", unsafe_allow_html=True)
    with vc4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Piezas por ticket</div>
            <div class="metric-value">{piezas_ticket:.1f}</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    vta_local = df_v_ult.groupby('local').agg(venta=('venta','sum'),ticket_prom=('ticket_prom','mean')).reset_index()
    vta_local['nombre'] = vta_local['local'].map(NOMBRES).fillna(vta_local['local'])
    vta_local = vta_local.sort_values('venta',ascending=True)
    fig_vta = px.bar(vta_local,x='venta',y='nombre',orientation='h',
        color='ticket_prom',color_continuous_scale=['#1e3a5f','#3b82f6','#60a5fa'],
        labels={'venta':'Venta $','nombre':'Local','ticket_prom':'Ticket prom.'},height=320)
    fig_vta.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(248,250,252,0.5)',
        font=dict(color='#334155',size=11),margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor='#e2e8f0'),
        coloraxis_colorbar=dict(title='Ticket prom.',tickformat='$,.0f'))
    fig_vta.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont_size=10)
    st.plotly_chart(fig_vta,use_container_width=True)

    if len(df_v['fecha'].unique())>1:
        df_v_trend = df_v.groupby(['fecha','semana']).agg(venta=('venta','sum')).reset_index()
        df_v_trend['periodo_sem'] = df_v_trend['fecha'].astype(str)+' S'+df_v_trend['semana'].astype(str)
        fig_vt = px.line(df_v_trend,x='periodo_sem',y='venta',height=220,
            color_discrete_sequence=['#3b82f6'],labels={'venta':'Venta $','periodo_sem':'Semana'})
        fig_vt.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(248,250,252,0.5)',
            font=dict(color='#334155',size=11),margin=dict(t=10,b=20,l=40,r=20),
            xaxis=dict(gridcolor='#e2e8f0',tickangle=45),yaxis=dict(gridcolor='#e2e8f0',tickformat='$,.0f'))
        st.plotly_chart(fig_vt,use_container_width=True)
    st.divider()

if not df_comp.empty:
    st.markdown('<p class="section-title">Compras</p>', unsafe_allow_html=True)
    df_c = df_comp.copy()
    df_c['monto'] = pd.to_numeric(df_c['monto'],errors='coerce').fillna(0)
    df_c_ult = df_c[df_c['fecha']==df_c['fecha'].max()]
    mercaderia  = df_c_ult[df_c_ult['Categoría']=='Mercadería']['monto'].sum()
    bonificacion = abs(df_c_ult[df_c_ult['Categoría']=='Bonificación']['monto'].sum())
    otros = df_c_ult[~df_c_ult['Categoría'].isin(['Mercadería','Bonificación'])]['monto'].sum()
    compra_neta = mercaderia - bonificacion + otros
    ratio_bonif = bonificacion/mercaderia*100 if mercaderia>0 else 0
    venta_ult = df_vta[df_vta['fecha']==df_vta['fecha'].max()]['venta'].sum() if not df_vta.empty else 0
    ratio_cv = compra_neta/venta_ult*100 if venta_ult>0 else 0
    color_cv = '#10b981' if ratio_cv<70 else '#f59e0b' if ratio_cv<85 else '#ef4444'

    cc1,cc2,cc3,cc4 = st.columns(4)
    with cc1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Compra bruta mercadería</div>
            <div class="metric-value">${mercaderia/1e6:.1f}M</div></div>""", unsafe_allow_html=True)
    with cc2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Bonificaciones recibidas</div>
            <div class="metric-value" style="color:#10b981">${bonificacion/1e6:.1f}M</div>
            <div class="metric-delta" style="color:#10b981">{ratio_bonif:.1f}% de la compra</div></div>""", unsafe_allow_html=True)
    with cc3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Compra neta</div>
            <div class="metric-value">${compra_neta/1e6:.1f}M</div></div>""", unsafe_allow_html=True)
    with cc4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Ratio compra/venta</div>
            <div class="metric-value" style="color:{color_cv}">{ratio_cv:.1f}%</div>
            <div class="metric-delta" style="color:#6b7280">meta &lt;70%</div></div>""", unsafe_allow_html=True)

    st.markdown("")
    comp_local = df_c_ult[df_c_ult['Categoría']=='Mercadería'].groupby('Local')['monto'].sum().reset_index()
    comp_local['nombre'] = comp_local['Local'].map(NOMBRES).fillna(comp_local['Local'])
    comp_local = comp_local.sort_values('monto',ascending=True)
    fig_comp = px.bar(comp_local,x='monto',y='nombre',orientation='h',
        color_discrete_sequence=['#7c3aed'],labels={'monto':'Compra $','nombre':'Local'},height=320)
    fig_comp.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(248,250,252,0.5)',
        font=dict(color='#334155',size=11),margin=dict(t=10,b=20,l=10,r=10),
        xaxis=dict(gridcolor='#e2e8f0'),showlegend=False)
    fig_comp.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont_size=10)
    st.plotly_chart(fig_comp,use_container_width=True)

    if len(df_c['fecha'].unique())>1:
        df_c_trend = df_c[df_c['Categoría']=='Mercadería'].groupby(['fecha','Semana']).agg(monto=('monto','sum')).reset_index()
        df_c_trend['periodo_sem'] = df_c_trend['fecha'].astype(str)+' S'+df_c_trend['Semana'].astype(str)
        fig_ct = px.line(df_c_trend,x='periodo_sem',y='monto',height=220,
            color_discrete_sequence=['#7c3aed'],labels={'monto':'Compra $','periodo_sem':'Semana'})
        fig_ct.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(248,250,252,0.5)',
            font=dict(color='#334155',size=11),margin=dict(t=10,b=20,l=40,r=20),
            xaxis=dict(gridcolor='#e2e8f0',tickangle=45),yaxis=dict(gridcolor='#e2e8f0',tickformat='$,.0f'))
        st.plotly_chart(fig_ct,use_container_width=True)

st.divider()
st.caption("Grupo Baco — Dashboard de gestión v1.0")
