import streamlit as st
import csv
from datetime import datetime
import io
import re

# --- Fonction pour lire le fichier CSV uploadé ---
def read_csv(uploaded_file):
    decoded = uploaded_file.read().decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(decoded))
    return list(csv_reader)

# --- Fonction pour générer le contenu XML SEPA ---
def generate_sepa_xml(virements, iban, bic, company_name):
    now = datetime.now().isoformat(timespec="seconds")
    total_amount = sum(float(v["montant"]) for v in virements)
    nb_of_txs = len(virements)

    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>SEPA-{now}</MsgId>
      <CreDtTm>{now}</CreDtTm>
      <NbOfTxs>{nb_of_txs}</NbOfTxs>
      <CtrlSum>{total_amount:.2f}</CtrlSum>
      <InitgPty>
        <Nm>{company_name}</Nm>
        <PstlAdr>
          <StrtNm>15 RUE DE PARIS</StrtNm>
          <PstCd>96500</PstCd>
          <TwnNm>GONESSE</TwnNm>
          <Ctry>FR</Ctry>
        </PstlAdr>

        <CtryOfRes>FR</CtryOfRes>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>SEPA-{now}</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <NbOfTxs>{nb_of_txs}</NbOfTxs>
      <CtrlSum>{total_amount:.2f}</CtrlSum>
      <PmtTpInf><SvcLvl><Cd>SEPA</Cd></SvcLvl></PmtTpInf>
      <ReqdExctnDt>{now[:10]}</ReqdExctnDt>
      <Dbtr>
        <Nm>{company_name}</Nm>
        <PstlAdr>
          <StrtNm>15 RUE DE PARIS</StrtNm>
          <PstCd>96500</PstCd>
          <TwnNm>GONESSE</TwnNm>
          <Ctry>FR</Ctry>
        </PstlAdr>
        <CtryOfRes>FR</CtryOfRes>
      </Dbtr>
      <DbtrAcct><Id><IBAN>{iban}</IBAN></Id></DbtrAcct>
      <DbtrAgt><FinInstnId><BIC>{bic}</BIC></FinInstnId></DbtrAgt>
"""
    tx_blocks = ""
    for v in virements:
        tx_blocks += f"""
      <CdtTrfTxInf>
        <PmtId><EndToEndId>{v['motif']}</EndToEndId></PmtId>
        <Amt><InstdAmt Ccy="EUR">{float(v['montant']):.2f}</InstdAmt></Amt>
        <CdtrAgt><FinInstnId><BIC>{v['bic']}</BIC></FinInstnId></CdtrAgt>
        <Cdtr>
          <Nm>{v['nom']}</Nm>
          <CtryOfRes>FR</CtryOfRes>
        </Cdtr>
        <CdtrAcct><Id><IBAN>{v['iban']}</IBAN></Id></CdtrAcct>
        <RmtInf><Ustrd>{now[:10]}/{v['motif']}</Ustrd></RmtInf>
      </CdtTrfTxInf>
"""
    footer = """
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""
    return header + tx_blocks + footer


# --- Interface Streamlit ---
st.title("💶 Générateur de fichier SEPA XML")
st.write("Déposez un fichier CSV contenant vos virements pour générer un fichier XML SEPA conforme.")

with st.expander("📘 Exemple de format CSV attendu", expanded=False):
    st.markdown("""
    Le fichier CSV doit contenir **exactement** les colonnes suivantes :
    ```
    nom,iban,montant,motif,bic
    Boulangerie du Marché,FR7612345678901234567890123,1250.00,Paiement facture 4589,AGRIFRPPXXX
    Société ABC,FR7611112222333344445555666,980.50,Paiement prestation mars,BDFEFRPPXXX
    Transport Express,FR7619988000012345678901234,152.75,Transport février,BNPAFRPPXXX
    ```
    💡 **Conseil** : Utilisez un point `.` pour les décimales, et ne mettez pas de séparateur de milliers.
    """)

uploaded_file = st.file_uploader("📤 Importer le fichier CSV", type=["csv"])

# --- Informations bancaires de l’émetteur ---
st.subheader("🏦 Informations bancaires de l’émetteur")

company_name = st.text_input("Nom de l’entreprise émettrice", value="Nom d'entreprise")
iban = st.text_input("IBAN (27 caractères pour un compte FR)", placeholder="FR76XXXXXXXXXXXXXX...")
bic = st.text_input("BIC (8 à 11 caractères)", placeholder="CEPAFRPPXXX")

# Validation IBAN/BIC
iban_valid = re.match(r"^FR\d{25}$", iban.replace(" ", "").upper()) if iban else False
bic_valid = re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", bic.upper()) if bic else False

if uploaded_file:
    try:
        virements = read_csv(uploaded_file)
        st.success(f"{len(virements)} virements trouvés dans le fichier.")

        if st.button("🚀 Générer le fichier SEPA XML"):
            if not company_name.strip():
                st.error("❌ Le nom de l’entreprise émettrice est obligatoire.")
            elif not iban_valid:
                st.error("❌ IBAN invalide. Il doit commencer par 'FR' et contenir 27 caractères.")
            elif not bic_valid:
                st.error("❌ BIC invalide. Il doit comporter 8 ou 11 caractères (lettres et chiffres).")
            else:
                xml_content = generate_sepa_xml(virements, iban.strip().upper(), bic.strip().upper(), company_name.strip())
                xml_bytes = io.BytesIO(xml_content.encode("utf-8"))

                st.download_button(
                    label="📥 Télécharger le fichier SEPA XML",
                    data=xml_bytes,
                    file_name=f"SEPA_{company_name.replace(' ', '_')}.xml",
                    mime="application/xml"
                )
                st.success(f"✅ Fichier SEPA généré avec succès pour {company_name} !")

    except Exception as e:
        st.error(f"Erreur lors du traitement du fichier : {e}")




