import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import date

st.set_page_config(page_title="Dashboard Grupo Baco", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.kcard { background:#f8fafc; border-radius:10px; padding:1rem 1.2rem; border:0.5px solid #e2e8f0; margin-bottom:4px; }
.klabel { font-size:11px; font-weight:500; letter-spacing:0.07em; text-transform:uppercase; color:#64748b; margin:0 0 6px; }
.kval { font-size:26px; font-weight:600; color:#0f172a; font-family:'DM Mono',monospace; margin:0; }
.ksub { font-size:12px; margin:4px 0 0; color:#64748b; }
.sec { font-size:11px; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:#94a3b8; margin:1.5rem 0 0.75rem; }
.tbl { width:100%; border-collapse:collapse; font-size:13px; }
.tbl th { font-size:11px; font-weight:500; color:#94a3b8; text-align:left; padding:4px 10px 8px; border-bottom:1px solid #e2e8f0; }
.tbl td { padding:8px 10px; border-bottom:0.5px solid #f1f5f9; color:#0f172a; }
.tbl tr:last-child td { border-bottom:none; }
.pill { display:inline-block; font-size:11px; font-weight:600; padding:3px 9px; border-radius:20px; }
.n5{background:#dcfce7;color:#15803d;} .n4{background:#dbeafe;color:#1d4ed8;}
.n3{background:#fef9c3;color:#a16207;} .n2{background:#fee2e2;color:#b91c1c;}
.n1{background:#fee2e2;color:#b91c1c;}
.tag-pagada{background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.tag-vencer{background:#fef9c3;color:#a16207;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.tag-vencida{background:#fee2e2;color:#b91c1c;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
.tag-novenc{background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;}
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

MESES_ORD = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
             'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}

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

def nota_ticket(v):
    if v>=10501: return 5
    elif v>=9501: return 4
    elif v>=8501: return 3
    elif v>=7501: return 2
    else: return 1

def pill(n):
    return f'<span class="pill n{n}">{n}</span>'

def nc(n, good_low=True):
    if good_low:
        return ['','#b91c1c','#b91c1c','#a16207','#1d4ed8','#15803d'][n]
    else:
        return ['','#b91c1c','#b91c1c','#a16207','#1d4ed8','#15803d'][n]

PLOT_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(248,250,252,0.5)',
    font=dict(color='#334155', size=11),
    margin=dict(t=30,b=30,l=50,r=20),
    xaxis=dict(gridcolor='#e2e8f0'),
    yaxis=dict(gridcolor='#e2e8f0')
)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Cargar datos")
    exist_file = st.file_uploader("Existencias (QlickView)", type="xlsx", key="dash_exist")
    des_file   = st.file_uploader("Desabasto (QlickView)",   type="xlsx", key="dash_des")
    vta_file   = st.file_uploader("Ventas (QlickView)",      type="xlsx", key="dash_vta")
    comp_file  = st.file_uploader("Facturación Simi (.xlsx)", type="xlsx", key="dash_comp",
        help="Archivo con hoja REGISTRO — se carga completo, reemplaza historial de compras")
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
            df_c = pd.read_excel(comp_file, sheet_name='REGISTRO')
            df_c.columns = [c.strip() for c in df_c.columns]
            df_c['Monto'] = pd.to_numeric(df_c['Monto'], errors='coerce').fillna(0)
            df_c['Fecha Documento'] = pd.to_datetime(df_c['Fecha Documento'], errors='coerce')
            df_c['Fecha Vencimiento'] = pd.to_datetime(df_c['Fecha Vencimiento'], errors='coerce')
            df_c.to_csv(HIST_COMP, index=False)
            guardado.append("compras")

        if guardado:
            st.success(f"Guardado: {', '.join(guardado)}")
            st.rerun()
        else:
            st.warning("Sube al menos un archivo para guardar")

# ── CARGAR HISTORIAL ──────────────────────────────────────────────────────────
df_inv  = pd.read_csv(HIST_INV)  if os.path.exists(HIST_INV)  else pd.DataFrame()
df_vta  = pd.read_csv(HIST_VTA)  if os.path.exists(HIST_VTA)  else pd.DataFrame()
df_comp = pd.read_csv(HIST_COMP) if os.path.exists(HIST_COMP) else pd.DataFrame()
if not df_comp.empty:
    df_comp.columns = [c.strip() for c in df_comp.columns]
    # Normalizar columnas clave
    for old_col, new_col in [('monto','Monto'),('categoría','Categoría'),('categoría ','Categoría'),
                               ('estatus','Estatus'),('año','Año'),('semana','Semana'),('local','Local')]:
        if old_col in df_comp.columns and new_col not in df_comp.columns:
            df_comp = df_comp.rename(columns={old_col: new_col})

# ── HEADER ────────────────────────────────────────────────────────────────────
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

# ── INVENTARIO ────────────────────────────────────────────────────────────────
if not df_inv.empty:
    st.markdown('<p class="sec">KPIs inventario — último período</p>', unsafe_allow_html=True)
    df_ult = df_inv[df_inv['fecha']==df_inv['fecha'].max()].copy()
    for col in ['des_pct','cat_pct','val_inv','dias_inv']:
        if col in df_ult.columns:
            df_ult[col] = pd.to_numeric(df_ult[col], errors='coerce').fillna(0)

    prom_des = df_ult['des_pct'].mean()
    prom_cat = df_ult['cat_pct'].mean()
    total_inv = df_ult['val_inv'].sum()
    mejor = df_ult.loc[df_ult['des_pct'].idxmin()]
    peor  = df_ult.loc[df_ult['des_pct'].idxmax()]
    nd_red = nota_des(prom_des)
    nc_red = nota_cat(prom_cat)

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="kcard"><p class="klabel">Desabasto red</p>
            <p class="kval" style="color:{nc(nd_red)}">{prom_des:.2f}%</p>
            <p class="ksub">{pill(nd_red)} meta ≤2.0% para nota 4</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="kcard"><p class="klabel">Catálogo vendido red</p>
            <p class="kval" style="color:{nc(nc_red)}">{prom_cat:.1f}%</p>
            <p class="ksub">{pill(nc_red)} meta &gt;70% para nota 3</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="kcard"><p class="klabel">Inventario total</p>
            <p class="kval">${total_inv/1e6:.0f}M</p>
            <p class="ksub">{len(df_ult)} locales activos</p></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="kcard"><p class="klabel">Rango desabasto</p>
            <p class="kval" style="font-size:18px;color:#15803d">{mejor['local']} {mejor['des_pct']:.2f}%</p>
            <p class="ksub" style="color:#b91c1c">peor: {peor['local']} {peor['des_pct']:.2f}%</p></div>""", unsafe_allow_html=True)

    st.markdown("")
    df_tbl = df_ult.copy()
    df_tbl['nombre'] = df_tbl['local'].map(NOMBRES).fillna(df_tbl['local'])
    df_tbl = df_tbl.sort_values('des_pct')
    rows_html = ""
    for _, r in df_tbl.iterrows():
        nd, ncat = nota_des(r['des_pct']), nota_cat(r['cat_pct'])
        dias_color = '#b91c1c' if r['dias_inv']>55 else '#a16207' if r['dias_inv']>35 else '#15803d'
        rows_html += f"""<tr>
            <td><strong>{r['local']}</strong><br><span style="color:#94a3b8;font-size:11px">{r['nombre']}</span></td>
            <td style="color:{nc(nd)};font-weight:500">{r['des_pct']:.2f}%</td>
            <td>{pill(nd)}</td>
            <td style="color:{nc(ncat)};font-weight:500">{r['cat_pct']:.1f}%</td>
            <td>{pill(ncat)}</td>
            <td>${r['val_inv']/1e6:.1f}M</td>
            <td style="color:{dias_color};font-weight:500">{r['dias_inv']:.0f}d</td>
        </tr>"""
    st.markdown(f"""<table class="tbl">
        <thead><tr><th>Local</th><th>Desabasto</th><th>Nota</th><th>Catálogo</th><th>Nota</th><th>Inventario</th><th>Días inv.</th></tr></thead>
        <tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

    if len(df_inv['fecha'].unique()) > 1:
        st.markdown('<p class="sec">Tendencia KPIs inventario</p>', unsafe_allow_html=True)
        df_trend = df_inv.groupby('fecha').agg(des_pct=('des_pct','mean'),cat_pct=('cat_pct','mean')).reset_index().sort_values('fecha')
        fig = make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Scatter(x=df_trend['fecha'],y=df_trend['des_pct'],name='Desabasto %',
            line=dict(color='#3b82f6',width=2),mode='lines+markers'),secondary_y=False)
        fig.add_trace(go.Scatter(x=df_trend['fecha'],y=df_trend['cat_pct'],name='Catálogo %',
            line=dict(color='#10b981',width=2,dash='dot'),mode='lines+markers'),secondary_y=True)
        fig.add_hline(y=2.0,line_dash="dash",line_color="#f59e0b",annotation_text="Meta nota 4",secondary_y=False)
        fig.update_layout(height=240,legend=dict(orientation='h',y=1.1),**PLOT_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    st.divider()

# ── VENTAS ────────────────────────────────────────────────────────────────────
if not df_vta.empty:
    st.markdown('<p class="sec">Ventas</p>', unsafe_allow_html=True)
    df_v = df_vta.copy()
    for col in ['venta','tickets','ticket_prom','piezas']:
        if col in df_v.columns:
            df_v[col] = pd.to_numeric(df_v[col],errors='coerce').fillna(0)
    df_v_ult = df_v[df_v['fecha']==df_v['fecha'].max()]
    venta_total = df_v_ult['venta'].sum()
    tickets_total = df_v_ult['tickets'].sum()
    ticket_prom = df_v_ult['ticket_prom'].mean()
    piezas_ticket = df_v_ult['piezas'].sum()/tickets_total if tickets_total>0 else 0
    nt = nota_ticket(ticket_prom)

    vc1,vc2,vc3,vc4 = st.columns(4)
    with vc1:
        st.markdown(f"""<div class="kcard"><p class="klabel">Venta total período</p>
            <p class="kval">${venta_total/1e6:.1f}M</p></div>""", unsafe_allow_html=True)
    with vc2:
        st.markdown(f"""<div class="kcard"><p class="klabel">Tickets totales</p>
            <p class="kval">{int(tickets_total):,}</p></div>""", unsafe_allow_html=True)
    with vc3:
        st.markdown(f"""<div class="kcard"><p class="klabel">Ticket promedio red</p>
            <p class="kval" style="color:{nc(nt)}">${ticket_prom:,.0f}</p>
            <p class="ksub">{pill(nt)} meta &gt;$9.501 nota 4</p></div>""", unsafe_allow_html=True)
    with vc4:
        st.markdown(f"""<div class="kcard"><p class="klabel">Piezas por ticket</p>
            <p class="kval">{piezas_ticket:.1f}</p></div>""", unsafe_allow_html=True)

    st.markdown("")
    col_vt1, col_vt2 = st.columns([1,1])
    with col_vt1:
        vta_local = df_v_ult.groupby('local').agg(venta=('venta','sum'),ticket_prom=('ticket_prom','mean')).reset_index()
        vta_local['nombre'] = vta_local['local'].map(NOMBRES).fillna(vta_local['local'])
        vta_local = vta_local.sort_values('venta',ascending=True)
        fig_vl = px.bar(vta_local,x='venta',y='nombre',orientation='h',height=320,
            color='ticket_prom',color_continuous_scale=['#bfdbfe','#1d4ed8'],
            labels={'venta':'','nombre':'','ticket_prom':'Ticket prom.'})
        fig_vl.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont_size=10)
        fig_vl.update_layout(coloraxis_colorbar=dict(title='Ticket',tickformat='$,.0f'),**PLOT_LAYOUT)
        st.plotly_chart(fig_vl,use_container_width=True)

    with col_vt2:
        rows_vta = ""
        for _, r in vta_local.sort_values('venta',ascending=False).iterrows():
            nt_loc = nota_ticket(r['ticket_prom'])
            rows_vta += f"""<tr>
                <td><strong>{r['local']}</strong><br><span style="color:#94a3b8;font-size:11px">{r['nombre']}</span></td>
                <td>${r['venta']/1e6:.1f}M</td>
                <td>{int(r['venta']/venta_total*100)}%</td>
                <td>${r['ticket_prom']:,.0f}</td>
                <td>{pill(nt_loc)}</td>
            </tr>"""
        st.markdown(f"""<table class="tbl">
            <thead><tr><th>Local</th><th>Venta</th><th>%</th><th>Ticket</th><th>Nota</th></tr></thead>
            <tbody>{rows_vta}</tbody></table>""", unsafe_allow_html=True)

    if len(df_v['fecha'].unique())>1:
        st.markdown('<p class="sec">Tendencia ventas semanal</p>', unsafe_allow_html=True)
        df_vt = df_v.groupby(['fecha','semana']).agg(venta=('venta','sum')).reset_index()
        df_vt['periodo_sem'] = df_vt['fecha'].astype(str)+' S'+df_vt['semana'].astype(str)
        fig_vt = px.line(df_vt,x='periodo_sem',y='venta',height=200,
            color_discrete_sequence=['#3b82f6'],labels={'venta':'','periodo_sem':''})
        fig_vt.update_layout(**{k:v for k,v in PLOT_LAYOUT.items() if k not in ['xaxis','yaxis']},
            xaxis=dict(gridcolor='#e2e8f0',tickangle=45),yaxis=dict(gridcolor='#e2e8f0',tickformat='$,.0f'))
        st.plotly_chart(fig_vt,use_container_width=True)
    st.divider()

# ── COMPRAS ───────────────────────────────────────────────────────────────────
if not df_comp.empty:
    st.markdown('<p class="sec">Compras y flujo de caja</p>', unsafe_allow_html=True)
    df_c = df_comp.copy()
    df_c['Monto'] = pd.to_numeric(df_c['Monto'],errors='coerce').fillna(0)
    df_c['Año']   = pd.to_numeric(df_c['Año'],   errors='coerce').fillna(0).astype(int)
    df_c['Semana']= pd.to_numeric(df_c['Semana'],errors='coerce').fillna(0).astype(int)

    # KPIs generales
    merc_total    = df_c[df_c['Categoría']=='Mercadería']['Monto'].sum()
    bonif_total   = abs(df_c[df_c['Categoría']=='Bonificación']['Monto'].sum())
    compra_neta   = merc_total - bonif_total
    ratio_bonif   = bonif_total/merc_total*100 if merc_total>0 else 0

    # Pendientes de pago
    pend = df_c[df_c['Estatus'].isin(['Por vencer','No vencido','Vencida'])]
    vencido   = pend[pend['Estatus']=='Vencida']['Monto'].sum()
    por_vencer= pend[pend['Estatus']=='Por vencer']['Monto'].sum()
    no_vencido= pend[pend['Estatus']=='No vencido']['Monto'].sum()
    total_pend= vencido + por_vencer + no_vencido

    cc1,cc2,cc3,cc4 = st.columns(4)
    with cc1:
        st.markdown(f"""<div class="kcard"><p class="klabel">Compra neta mercadería</p>
            <p class="kval">${compra_neta/1e6:.0f}M</p>
            <p class="ksub">bonif. {ratio_bonif:.1f}% — ${bonif_total/1e6:.0f}M recibido</p></div>""", unsafe_allow_html=True)
    with cc2:
        st.markdown(f"""<div class="kcard"><p class="klabel">Total por pagar</p>
            <p class="kval" style="color:#b91c1c">${total_pend/1e6:.0f}M</p>
            <p class="ksub">vencido + por vencer + no vencido</p></div>""", unsafe_allow_html=True)
    with cc3:
        st.markdown(f"""<div class="kcard"><p class="klabel">Vencido — urgente</p>
            <p class="kval" style="color:#b91c1c">${vencido/1e6:.0f}M</p>
            <p class="ksub" style="color:#b91c1c">requiere pago inmediato</p></div>""", unsafe_allow_html=True)
    with cc4:
        st.markdown(f"""<div class="kcard"><p class="klabel">Por vencer pronto</p>
            <p class="kval" style="color:#a16207">${por_vencer/1e6:.0f}M</p>
            <p class="ksub">${no_vencido/1e6:.0f}M no vencido aún</p></div>""", unsafe_allow_html=True)

    st.markdown("")
    col_c1, col_c2 = st.columns([1,1])

    with col_c1:
        st.markdown('<p class="sec">Compra semanal mercadería (últimas 12 semanas)</p>', unsafe_allow_html=True)
        merc_sem = df_c[df_c['Categoría']=='Mercadería'].groupby(['Año','Semana'])['Monto'].sum().reset_index()
        merc_sem = merc_sem.sort_values(['Año','Semana']).tail(12)
        merc_sem['periodo'] = merc_sem['Año'].astype(str) + ' S' + merc_sem['Semana'].astype(str)
        fig_cs = px.bar(merc_sem,x='periodo',y='Monto',height=260,
            color_discrete_sequence=['#7c3aed'],labels={'Monto':'','periodo':''})
        fig_cs.update_traces(texttemplate='$%{y:,.0f}',textposition='outside',textfont_size=9)
        fig_cs.update_layout(**{k:v for k,v in PLOT_LAYOUT.items() if k not in ['xaxis','yaxis']},
            xaxis=dict(gridcolor='#e2e8f0',tickangle=45),yaxis=dict(gridcolor='#e2e8f0',tickformat='$,.0f'))
        st.plotly_chart(fig_cs,use_container_width=True)

    with col_c2:
        st.markdown('<p class="sec">Estado de facturas pendientes</p>', unsafe_allow_html=True)
        fig_est = go.Figure(go.Bar(
            x=[vencido, por_vencer, no_vencido],
            y=['Vencida','Por vencer','No vencido'],
            orientation='h',
            marker_color=['#ef4444','#f59e0b','#3b82f6'],
            text=[f'${vencido/1e6:.0f}M',f'${por_vencer/1e6:.0f}M',f'${no_vencido/1e6:.0f}M'],
            textposition='outside',textfont_size=11
        ))
        fig_est.update_layout(height=200,showlegend=False,**PLOT_LAYOUT)
        st.plotly_chart(fig_est,use_container_width=True)

        # Por categoria
        st.markdown('<p class="sec">Por categoría (histórico)</p>', unsafe_allow_html=True)
        cat_res = df_c.groupby('Categoría')['Monto'].sum().reset_index().sort_values('Monto',ascending=False)
        rows_cat = ""
        for _, r in cat_res.iterrows():
            color = '#15803d' if r['Monto']<0 else '#0f172a'
            rows_cat += f"<tr><td>{r['Categoría']}</td><td style='color:{color};font-weight:500;text-align:right'>${r['Monto']/1e6:.1f}M</td></tr>"
        st.markdown(f"""<table class="tbl">
            <thead><tr><th>Categoría</th><th style="text-align:right">Monto</th></tr></thead>
            <tbody>{rows_cat}</tbody></table>""", unsafe_allow_html=True)

    # Compra por local (últimas 4 semanas)
    st.markdown('<p class="sec">Compra por local — últimas 4 semanas</p>', unsafe_allow_html=True)
    ult_sem = merc_sem.tail(4)['Semana'].tolist()
    ult_ano = merc_sem.tail(4)['Año'].tolist()
    merc_local = df_c[
        (df_c['Categoría']=='Mercadería') &
        (df_c['Semana'].isin(ult_sem))
    ].groupby('Local')['Monto'].sum().reset_index()
    merc_local['nombre'] = merc_local['Local'].map(NOMBRES).fillna(merc_local['Local'])
    merc_local = merc_local.sort_values('Monto',ascending=True)
    fig_cl = px.bar(merc_local,x='Monto',y='nombre',orientation='h',height=300,
        color_discrete_sequence=['#7c3aed'],labels={'Monto':'','nombre':''})
    fig_cl.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',textfont_size=10)
    fig_cl.update_layout(**PLOT_LAYOUT)
    st.plotly_chart(fig_cl,use_container_width=True)

st.divider()
st.caption("Grupo Baco — Dashboard de gestión v1.0")
