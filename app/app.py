"""
Dashboard — Retards des vols intérieurs US (BTS 2024)
Pour la directrice des opérations d'une compagnie aérienne.

Récit en trois temps : Contexte (4 KPI, tendance mensuelle) → Constat (causes, carte des aéroports,
créneaux à risque) → Recommandation (routes à traiter en premier, phrase d'action).

Lit les tables gold_* de PostgreSQL (écrites par notebooks/03_gold.ipynb). Si elles sont absentes, le
dashboard affiche des données FICTIVES au format du contrat, avec un bandeau d'avertissement.
Forcer les données fictives : variable d'environnement DONNEES_FICTIVES=1.
"""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from donnees_fictives import tables_fictives

st.set_page_config(page_title="Retards des vols US — Dashboard", page_icon="✈️", layout="wide")

# ── Palette : une seule couleur d'accent, qui veut toujours dire « là où agir » ─────────────────────────────
ACCENT = "#257de0"
GRIS = "#b4b4b4"
ENCRE, ENCRE_2, GRILLE, AXE = "#191919", "#666666", "#e7e7e7", "#c2c2c2"
SEQUENTIEL = [[0.0, "#cce3fd"], [0.17, "#9dc8f7"], [0.33, "#6aabf1"], [0.5, "#338ced"],
              [0.67, "#2370cd"], [0.83, "#1757ac"], [1.0, "#0e3d7e"]]   # une teinte, du clair au foncé
POLICE = "system-ui, -apple-system, 'Segoe UI', sans-serif"

TABLES = ["gold_ponctualite_mensuelle", "gold_causes_retard", "gold_aeroports", "gold_heure_jour", "gold_routes"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]
MOIS_ABR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
LIBELLES_CAUSES = {
    "avion_retard": "Avion en retard (vol précédent)",
    "compagnie": "Compagnie (équipage, maintenance, sol)",
    "nas": "Système national (contrôle aérien, trafic)",
    "meteo": "Météo extrême",
    "securite": "Sécurité",
}
TOUS_AEROPORTS = "Tous les aéroports"


def pct(x, d=1):
    """74.83 → « 74,8 % »."""
    return f"{x:.{d}f}".replace(".", ",") + " %"


def milliers(n):
    return f"{int(round(n)):,}".replace(",", " ")


# ── Données ───────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner="Lecture des tables gold…")
def charger():
    """Renvoie (tables, source, détail). source = « postgres » ou « fictif »."""
    if os.getenv("DONNEES_FICTIVES") == "1":
        return tables_fictives(), "fictif", "variable DONNEES_FICTIVES=1"
    try:
        import sqlalchemy
        url = (f"postgresql+psycopg2://{os.getenv('PG_USER', 'cours')}:{os.getenv('PG_PASSWORD', 'cours')}"
               f"@{os.getenv('PG_HOST', 'localhost')}:{os.getenv('PG_PORT', '5432')}/{os.getenv('PG_DB', 'vols')}")
        moteur = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 3})
        with moteur.connect() as connexion:
            tables = {t: pd.read_sql(sqlalchemy.text(f"SELECT * FROM {t}"), connexion) for t in TABLES}
        return tables, "postgres", ""
    except Exception as erreur:   # base absente, tables pas encore créées, mauvais identifiants…
        return tables_fictives(), "fictif", f"{type(erreur).__name__} : {str(erreur).splitlines()[0][:160]}"


def avec_comptes(df, vols="vols"):
    """Comptes nécessaires pour ré-agréger (03_gold les fournit). S'ils manquent (contrat strict), on les
    reconstitue à partir des pourcentages : les détournés (≈ 0,25 % des vols) restent alors comptés opérés."""
    df = df.copy()
    if "vols_operes" not in df:
        df["vols_annules"] = df[vols] * df["pct_annules"] / 100
        df["vols_operes"] = df[vols] - df["vols_annules"]
        df["vols_a_l_heure"] = df["vols_operes"] * df["pct_a_l_heure"] / 100
    return df


def ponctualite_de(df):
    """Ponctualité ré-agrégée à partir des comptes (jamais la moyenne des pourcentages)."""
    return 100 * df.vols_a_l_heure.sum() / df.vols_operes.sum() if df.vols_operes.sum() else float("nan")


tables, SOURCE, DETAIL = charger()
ponctualite = avec_comptes(tables["gold_ponctualite_mensuelle"])
ponctualite["mois"] = pd.to_datetime(ponctualite["mois"])
causes = tables["gold_causes_retard"].copy()
causes["mois"] = pd.to_datetime(causes["mois"])
aeroports = avec_comptes(tables["gold_aeroports"], vols="departs")
heure_jour = tables["gold_heure_jour"]
routes = tables["gold_routes"]


# ── Style des graphiques ──────────────────────────────────────────────────────────────────────────────────
def styler(fig, conclusion, mesure, hauteur=420):
    """Titre = la conclusion, sous-titre gris = ce qui est mesuré ; fond blanc, grille discrète."""
    fig.update_layout(
        title=dict(text=f"<b>{conclusion}</b><br><span style='font-size:13px;color:{ENCRE_2}'>{mesure}</span>",
                   x=0, xanchor="left", font=dict(size=17, color=ENCRE)),
        font=dict(family=POLICE, color=ENCRE, size=13), height=hauteur, showlegend=False,
        separators=", ",                      # virgule décimale, espace pour les milliers
        plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=10, r=30, t=86, b=40),
        hoverlabel=dict(bgcolor="white", font=dict(family=POLICE, color=ENCRE)),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXE, tickcolor=AXE, tickfont=dict(color=ENCRE_2),
                     title_font=dict(color=ENCRE_2), automargin=True)
    fig.update_yaxes(showgrid=False, linecolor=AXE, tickcolor=AXE, tickfont=dict(color=ENCRE_2),
                     title_font=dict(color=ENCRE_2), automargin=True)
    return fig


def afficher(fig):
    st.plotly_chart(fig, theme=None, width="stretch", config={"displaylogo": False})


def portee(compagnie, periode, aeroport):
    """Dit, sous chaque graphique, quels filtres s'y appliquent (les tables gold n'ont pas toutes les dimensions)."""
    actifs = {"compagnie": compagnie, "période": periode, "aéroport": aeroport}
    oui = [f for f, a in actifs.items() if a]
    non = [f for f, a in actifs.items() if not a]
    texte = f"Filtres appliqués : {', '.join(oui)}." if oui else "Aucun filtre ne s'applique à ce graphique."
    if non:
        texte += f" Non filtré par {' ni '.join(non)} : la table gold n'a pas ce détail (année 2024 entière, toutes compagnies)."
    st.caption(texte)


def barres_horizontales(etiquettes, valeurs, couleurs, textes, survol, titre_axe, x_max=None):
    """Barres horizontales triées (la première en haut), axe à 0, valeur écrite au bout de chaque barre."""
    fig = go.Figure(go.Bar(
        x=valeurs, y=etiquettes, orientation="h", marker=dict(color=couleurs, line=dict(width=0)),
        text=textes, textposition="outside", cliponaxis=False, textfont=dict(color=ENCRE, size=12),
        hovertext=survol, hovertemplate="%{hovertext}<extra></extra>"))
    fig.update_layout(bargap=0.3)
    fig.update_yaxes(autorange="reversed", ticks="", showline=False)
    fig.update_xaxes(range=[0, x_max or max(valeurs) * 1.25], title_text=titre_axe, showgrid=True,
                     gridcolor=GRILLE, zeroline=True, zerolinecolor=AXE)
    return fig


# ── En-tête et filtres (une seule ligne, au-dessus de tout ce qu'ils filtrent) ──────────────────────────────
st.title("Retards des vols intérieurs américains en 2024")
st.markdown("**Pour la directrice des opérations** : où, quand et pourquoi les vols arrivent-ils en retard, "
            "et par quoi commencer pour améliorer la ponctualité ?")

if SOURCE == "fictif":
    st.warning(
        "**Données fictives** : les tables gold ne sont pas lisibles dans PostgreSQL "
        f"({DETAIL}). Les graphiques montrent des valeurs inventées au format du contrat gold ; "
        "**n'en tirez aucune conclusion**. Lancez les notebooks 01 → 03 (docker compose up -d) puis rechargez la page.",
        icon="⚠️")

noms_compagnies = (ponctualite.groupby("compagnie_nom").vols.sum().sort_values(ascending=False).index.tolist())
mois_disponibles = [pd.Timestamp(m) for m in sorted(ponctualite.mois.unique())]
aeroports_tries = aeroports.sort_values("departs", ascending=False)
choix_aeroports = [TOUS_AEROPORTS] + [f"{c} · {v}" for c, v in zip(aeroports_tries.code_iata, aeroports_tries.ville)]

f1, f2, f3 = st.columns([2, 2, 1.4])
selection = f1.multiselect("Compagnie(s)", noms_compagnies, placeholder="Toutes les compagnies",
                           help="Vide = toutes les compagnies. Les KPI se comparent alors au marché.")
debut, fin = f2.select_slider(
    "Période", options=mois_disponibles, value=(mois_disponibles[0], mois_disponibles[-1]),
    format_func=lambda d: f"{MOIS_ABR[d.month - 1]} {d.year}")
choix_aeroport = f3.selectbox("Aéroport", choix_aeroports,
                              help="Met l'aéroport en évidence sur la carte et filtre les routes qui le desservent.")
code_aeroport = None if choix_aeroport == TOUS_AEROPORTS else choix_aeroport.split(" · ")[0]

dans_periode = ponctualite.mois.between(debut, fin)
marche = ponctualite[dans_periode]                                     # toutes compagnies, même période
selectionne = marche[marche.compagnie_nom.isin(selection)] if selection else marche
if len(selection) == 1:      # pour accorder les titres : « que Delta contrôle », « des compagnies choisies »…
    sujet, sujet_de, verbe = selection[0], f"de {selection[0]}", "contrôle"
elif selection:
    sujet, sujet_de, verbe = "les compagnies choisies", "des compagnies choisies", "contrôlent"
else:
    sujet, sujet_de, verbe = "les compagnies", "de l'ensemble des compagnies", "contrôlent"
codes_selection = ponctualite.loc[ponctualite.compagnie_nom.isin(selection), "compagnie_code"].unique()
causes_periode = causes[causes.mois.between(debut, fin)]
causes_sel = causes_periode[causes_periode.compagnie_code.isin(codes_selection)] if selection else causes_periode


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. CONTEXTE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
st.header("1 · Contexte : où en est la ponctualité ?")


def kpis(df, df_causes):
    vols_operes = df.vols_operes.sum()
    return {
        "ponctualite": ponctualite_de(df),
        "retard": (df.retard_moyen_min * df.vols_operes).sum() / vols_operes if vols_operes else float("nan"),
        "annulations": 100 * df.vols_annules.sum() / df.vols.sum() if df.vols.sum() else float("nan"),
        "controlable": (100 * df_causes.loc[df_causes.controlable.astype(bool), "minutes"].sum()
                        / df_causes.minutes.sum()) if df_causes.minutes.sum() else float("nan"),
    }


k = kpis(selectionne, causes_sel)
k_marche = kpis(marche, causes_periode)


def ecart(cle, unite, d=1):
    """Écart à l'ensemble des compagnies, affiché seulement quand une compagnie est choisie."""
    if not selection or np.isnan(k[cle]) or np.isnan(k_marche[cle]):
        return None
    v = k[cle] - k_marche[cle]
    return f"{v:+.{d}f}".replace(".", ",") + f" {unite} vs marché"


FICHES = {
    "ponctualite": dict(
        titre="Ponctualité à l'arrivée", valeur=lambda: pct(k["ponctualite"]), delta=ecart("ponctualite", "pt"),
        couleur="normal",
        definition="Part des vols **opérés** (ni annulés, ni détournés) arrivés avec **moins de 15 minutes** de "
                   "retard : c'est la définition du ministère américain des Transports (ARR_DEL15 = 0).",
        calcul="`100 × Σ vols_a_l_heure / Σ vols_operes` sur `gold_ponctualite_mensuelle`, pour les compagnies et "
               "les mois choisis. On somme les comptes avant de diviser : un mois de 120 000 vols pèse plus qu'un "
               "mois de 6 000 (jamais de moyenne de pourcentages).",
        interet="L'indicateur de référence, publié chaque mois par le DOT et suivi par les passagers. C'est lui "
                "que les actions doivent faire monter ; l'écart au marché situe la compagnie face à ses concurrentes."),
    "retard": dict(
        titre="Retard moyen à l'arrivée", valeur=lambda: f"{k['retard']:.1f} min".replace(".", ","),
        delta=ecart("retard", "min"), couleur="inverse",
        definition="Retard moyen à l'arrivée des vols opérés, en minutes. Les vols en avance comptent en négatif.",
        calcul="`Σ (retard_moyen_min × vols_operes) / Σ vols_operes` : moyenne des mois et compagnies, pondérée "
               "par leurs vols opérés.",
        interet="La ponctualité dit **combien** de vols sont en retard, pas **de combien**. Le retard moyen mesure "
                "l'ampleur, qui fait les correspondances manquées, les heures supplémentaires d'équipage et les "
                "indemnisations."),
    "annulations": dict(
        titre="Taux d'annulation", valeur=lambda: pct(k["annulations"], 2), delta=ecart("annulations", "pt", 2),
        couleur="inverse",
        definition="Part des vols **programmés** qui ont été annulés.",
        calcul="`100 × Σ vols_annules / Σ vols` sur `gold_ponctualite_mensuelle` (colonne `pct_annules` "
               "ré-agrégée).",
        interet="Une annulation coûte plus cher qu'un retard (réacheminement, hébergement). Comme les vols annulés "
                "sont exclus de la ponctualité, il faut les suivre à part : sinon annuler un vol fragile "
                "améliorerait artificiellement la ponctualité."),
    "controlable": dict(
        titre="Part des retards contrôlables", valeur=lambda: pct(k["controlable"]),
        delta=ecart("controlable", "pt"), couleur="off",
        definition="Part des minutes de retard dues à une cause **sur laquelle la compagnie peut agir** : "
                   "la compagnie elle-même (équipage, maintenance, opérations au sol) ou l'avion arrivé en retard "
                   "de son vol précédent (rotations).",
        calcul="`Σ minutes (causes compagnie + avion_retard) / Σ minutes des cinq causes` sur "
               "`gold_causes_retard` (colonne `controlable`). On somme les minutes avant de diviser.",
        interet="Dit quelle part du problème la compagnie peut réduire **elle-même**, sans attendre la météo ni le "
                "contrôle aérien. C'est l'ambition réaliste d'un plan d'action."),
}

colonnes = st.columns(4)
for colonne, (cle, fiche) in zip(colonnes, FICHES.items()):
    with colonne:
        st.metric(fiche["titre"], fiche["valeur"](), fiche["delta"], delta_color=fiche["couleur"], border=True)
        with st.expander("Fiche KPI"):
            st.markdown(f"**Définition.** {fiche['definition']}\n\n**Calcul.** {fiche['calcul']}\n\n"
                        f"**Intérêt pour la directrice.** {fiche['interet']}")

periode_txt = (f"de {MOIS[debut.month - 1]} à {MOIS[fin.month - 1]} {fin.year}" if debut != fin
               else f"en {MOIS[debut.month - 1]} {debut.year}")
st.caption(f"{milliers(selectionne.vols.sum())} vols programmés {periode_txt}"
           + (f" pour {', '.join(selection)}" if selection else ", toutes compagnies")
           + (". Écarts calculés par rapport à l'ensemble des compagnies sur la même période." if selection else "."))

# Courbe mensuelle : la sélection en bleu, le marché en gris comme référence
mensuel_sel = selectionne.groupby("mois")[["vols_operes", "vols_a_l_heure"]].sum()
mensuel_sel["pct"] = 100 * mensuel_sel.vols_a_l_heure / mensuel_sel.vols_operes
mensuel_marche = marche.groupby("mois")[["vols_operes", "vols_a_l_heure"]].sum()
mensuel_marche["pct"] = 100 * mensuel_marche.vols_a_l_heure / mensuel_marche.vols_operes

fig = go.Figure()
series = [(mensuel_sel, ACCENT, "Sélection" if selection else "Toutes compagnies", 2.5)]
if selection:
    series.insert(0, (mensuel_marche, GRIS, "Marché", 2))
for donnees, couleur, nom, epaisseur in series:
    fig.add_trace(go.Scatter(
        x=donnees.index, y=donnees.pct, mode="lines+markers", name=nom,
        line=dict(color=couleur, width=epaisseur), marker=dict(size=8, color=couleur, line=dict(color="white", width=2)),
        hovertemplate=f"<b>{nom}</b><br>%{{x|%B %Y}}<br>%{{y:.1f}} % à l'heure<extra></extra>"))
    fig.add_annotation(x=donnees.index[-1], y=donnees.pct.iloc[-1], text=f"<b>{nom}</b>" if couleur == ACCENT else nom,
                       xanchor="left", xshift=10, showarrow=False, font=dict(color=ENCRE if couleur == ACCENT else ENCRE_2))
creux, pic = mensuel_sel.pct.idxmin(), mensuel_sel.pct.idxmax()
toutes = pd.concat([mensuel_sel.pct, mensuel_marche.pct if selection else mensuel_sel.pct])
bas = 5 * np.floor(toutes.min() / 5) - 10
if len(mensuel_sel) > 1:
    conclusion = (f"Ponctualité {sujet_de} : creux en {MOIS[creux.month - 1]} ({pct(mensuel_sel.pct[creux])}), "
                  f"pic en {MOIS[pic.month - 1]} ({pct(mensuel_sel.pct[pic])})")
else:
    conclusion = f"Ponctualité {sujet_de} en {MOIS[creux.month - 1]} : {pct(mensuel_sel.pct[creux])}"
styler(fig, conclusion, "Part des vols opérés arrivés avec moins de 15 min de retard, par mois"
       + (" ; en gris, l'ensemble des compagnies" if selection else ""), hauteur=380)
fig.update_yaxes(range=[bas, max(bas + 30, 5 * np.ceil(toutes.max() / 5) + 5)], ticksuffix=" %",
                 title_text="Vols à l'heure (%)", showgrid=True, gridcolor=GRILLE)
fig.update_xaxes(tickvals=mensuel_sel.index, ticktext=[MOIS_ABR[d.month - 1] for d in mensuel_sel.index],
                 title_text=None, range=[mensuel_sel.index[0] - pd.Timedelta(days=12), mensuel_sel.index[-1] + pd.Timedelta(days=12)])
fig.update_layout(margin=dict(r=110))
afficher(fig)
portee(compagnie=True, periode=True, aeroport=False)


# ── Pied de page ──────────────────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Source : Bureau of Transportation Statistics, *Reporting Carrier On-Time Performance*, 2024 (vols intérieurs, "
    "compagnie opérante). Chaîne : CSV → bronze → silver → gold (Spark, Delta Lake, RustFS) → PostgreSQL → ce "
    "dashboard. « À l'heure » = arrivé avec moins de 15 min de retard (définition du DOT) ; annulés et détournés "
    "exclus du dénominateur de ponctualité, comptés dans le taux d'annulation. "
    + ("Données lues dans PostgreSQL (tables gold_*)." if SOURCE == "postgres" else "**Données fictives.**"))
