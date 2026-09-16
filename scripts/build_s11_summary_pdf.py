"""Render the English technical summary using the bundled document runtime."""
import json
import shutil
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=ROOT/'delivery/s11'


def main():
    dest=ROOT/'output/pdf/S11_Model_Summary.pdf'; dest.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    for name in ('Title','Heading1','Heading2','Normal'):
        styles[name].textColor=colors.black
        styles[name].fontName='Helvetica-Bold' if name!='Normal' else 'Helvetica'
    styles['Normal'].fontSize=10; styles['Normal'].leading=14; styles['Normal'].spaceAfter=8
    styles['Title'].fontSize=22; styles['Title'].leading=27; styles['Title'].alignment=TA_LEFT
    styles['Heading1'].fontSize=15; styles['Heading1'].spaceBefore=8; styles['Heading1'].spaceAfter=9
    styles['Heading2'].fontSize=11; styles['Heading2'].spaceBefore=7
    story=[]
    def p(text,style='Normal'): story.append(Paragraph(text,styles[style]))
    def table(rows,widths):
        cells=[[Paragraph(escape(str(v)),styles['Normal']) for v in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eef2')),
                              ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#cdd3d8')),
                              ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),8),
                              ('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),
                              ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.append(t); story.append(Spacer(1,12))
    p('S11 precipitation forecasting','Title')
    p('Technical model summary for WORCAP 2026','Heading2')
    p('Competition: Previsao Climatica de Precipitacao sobre a America do Sul. '
      'Prepared for the INPE WORCAP competition organizer. This document describes the '
      'S11 model submitted by the entrant, its reproducibility package and its limitations. '
      'Public RMSE 1.71718 was reported by the entrant; private score and final rank are not yet known.')
    p('Model overview','Heading1')
    p('S11 is a regularized convex recalibration of five official-data model components derived from S10. '
      'It combines spatial-context gradient boosting, local ridge regressions, regional atmospheric '
      'modes, continental partial least squares and a fine-scale tropical partial least squares model. '
      'Atmospheric conditions in month M predict mean daily precipitation in month M+1. '
      'All rainfall training targets end in December 2022; no 2023 or 2024 rainfall target is used. '
      'The final learner configuration is frozen, with no additional search during delivery reproduction.')
    p('Reported results and scope','Heading1')
    table([['Evaluation','S10','S11'],['Public leaderboard 2023','1.71895','1.71718'],
           ['Historical 2009-2020','1.775343','1.774622'],['Reused 2021-2022','1.830283','1.829353'],
           ['Reused 2022 alone','1.840430','1.841992']],[220,127,128])
    p('S11 reduced public RMSE by 0.00177, approximately 0.103%. This is not a statistical '
      'significance claim and does not establish improvement on private 2024 targets. Historical '
      'development improved in four of six blocks and six of twelve years; the internal approval '
      'criteria were not met. The entrant explicitly authorized this experimental submission.')
    p('Entrant information','Heading1')
    p('The team name, member identities, contact details, backgrounds, role allocation and time spent '
      'must be supplied by the entrant in TEAM_INFO.json before sponsor delivery. These facts are not '
      'inferred from account or filesystem names. The private score and rank must be completed only '
      'after the official result. License selection is recorded separately and requires entrant approval.')
    story.append(PageBreak())
    p('Data and model specification','Heading1')
    p('The official ERA5 data cover a 301 by 261 grid at 0.25 degrees: latitude -60 to 15 and '
      'longitude -90 to -25. There are 78,561 cells per month. The submission contains 1,885,464 '
      'rows across January 2023 to December 2024. The sample file controls ID order; output columns '
      'are id and tp_mm_day. RMSE uses every cell and month uniformly, including ocean points.')
    p('Inputs and feature engineering','Heading2')
    p('Nine atmospheric variables are used: 2 m temperature, cloud cover, surface pressure, and '
      'specific humidity, relative humidity, temperature, geopotential, zonal wind and meridional '
      'wind at 850 hPa. Features include calendar seasonality, coordinates, causal anomalies, '
      'three-month atmospheric averages, month-to-month changes, spatial averages and '
      'humidity-wind interactions in the context trees. A trailing 60-year monthly rainfall '
      'climatology provides the baseline. This is a feature inventory, not an empirical importance ranking.')
    table([['Component','Frozen specification'],
           ['S02','Context trees 300 iterations and local trees 150 iterations; ridge penalty 0.1 and climatology.'],
           ['Regional modes','PCA16, trailing atmospheric mean over 3 months, seasonal interactions and ridge penalty 0.3.'],
           ['Local memory','18 atmospheric anomaly features, seasonal windows and ridge penalty 0.3 per grid cell.'],
           ['Continental PLS','PCA64 atmospheric modes, PLS16 latent scores, rainfall EOF32 and ridge output penalty 0.3.'],
           ['Tropical PLS','Continental and 1-degree tropical PCA64 inputs, PLS32, rainfall EOF32; original-grid outputs.']],[125,350])
    p('Final combination','Heading2')
    p('Five-component weights vary across 12 fixed season/latitude groups. They are nonnegative, '
      'sum to one, and stay within 0.10 of the S10 prior. Lambda is 1. The tropical component is '
      'extended by S09 outside its domain, with a linear transition from 15 S to 10 S. '
      'Final weights and all preprocessing parameters are serialized; exact arrays are in the model package.')
    p('All base learners use 503 final training pairs from January 1981 observations through '
      'November 2022 observations, targeting through December 2022. A simple climatology-only '
      'submission previously scored 1.85468 publicly. No sub-ten-feature model has been established '
      'as retaining 90-95% of the final performance; no such claim is made.')
    story.append(PageBreak())
    p('Reproduction and computing environment','Heading1')
    p('The delivery separates raw preparation, final training and inference. All path roots are '
      'configured in SETTINGS.json. Inference loads serialized learners and does not read training '
      'rainfall or cached prediction arrays. Raw competition files are not distributed in the archive; '
      'the organizer or entrant supplies them after accepting the data terms.')
    p('Final-training verification','Heading2')
    comp=json.loads((DELIVERY/'verification/reproduction_comparison.json').read_text())
    p('All five base components were retrained in an isolated directory from official raw-derived arrays. '
      'The resulting CSV exactly matches the original S11 SHA-256. Before CSV rounding, the largest '
      f'prediction difference was {comp["full_prediction_max_abs_difference"]:.3g} mm/day. '
      'The difference reflects floating-point calculations and disappears at the exported precision.')
    p('The final ensemble calibration is reproduced from archived out-of-fold covariance sufficient '
      'statistics for 2005-2022 and the frozen S10 prior. These are fitted historical artifacts '
      'with provenance, not raw observations. The delivery test does not repeat the entire '
      'historical search or regenerate every calibration fold from raw data. This limitation is '
      'explicit; it must not be described as a complete from-zero replay of the research history.')
    p('Measured reference run','Heading2')
    rows=[['Stage','Elapsed seconds','Peak process memory']]
    for name in ('prepare','train','predict'):
        r=json.loads((DELIVERY/f'verification/{name}_execution.json').read_text())
        rows.append([name,f'{r["seconds"]:.1f}',f'{r["process_peak_working_set_bytes"]/1024**3:.2f} GiB'])
    table(rows,[170,130,175])
    p('Host: Intel Core i5-1135G7 at 2.40 GHz, 4 physical cores and 8 logical processors; '
      'approximately 16 GB RAM; Windows build 26200; Python 3.11.1. Computation uses one '
      'BLAS/OpenMP thread and no GPU. These timings describe this run on this host, not universal '
      'performance guarantees or minimum RAM requirements.')
    p('Dependency portability','Heading2')
    p('The original package index did not resolve the pinned versions in this environment. Offline '
      'Windows x64 wheels were repacked from installed distributions, with version and file hashes, '
      'license notices and provenance. They are not presented as original publisher wheels. '
      'A separate Python environment is used for installation and standalone execution checks. '
      'The verification directory records the final test status and any remaining limitations.')
    story.append(PageBreak())
    p('Validation governance and handoff','Heading1')
    p('The internal selection criteria remain active. S11 was a one-off explicit exception, not '
      'a relaxation of the thresholds. A later public improvement does not retrospectively '
      'approve a historically rejected candidate. Generation of a new candidate and any upload '
      'require an explicit entrant request. This delivery test reproduces an existing entry only.')
    p('Approval criteria','Heading2')
    p('Development requires at least 0.3% pooled RMSE improvement, better second-year aggregate, '
      'improvement in at least 5 of 6 blocks, 9 of 12 years and 55% of months, and worst annual '
      'relative degradation no greater than 0.5%. Confirmation requires at least 0.1% aggregate '
      'gain and improvement in both years. Test-year correction RMS must not exceed twice '
      'historical correction RMS. The historical periods have been reused and are not independent holdouts.')
    p('Limitations and findings','Heading2')
    p('The work suggests complementary local, regional and tropical atmospheric representations '
      'can help this task. It does not isolate each contribution causally. No feature-importance '
      'ranking, private-score estimate or guarantee of reaching 1.70 is asserted. The public '
      'leaderboard is only one historical year. The serialized runtime is constrained to the '
      'competition grid and forecast calendar; adapting it to a different domain requires new validation.')
    p('Delivery controls','Heading2')
    p('The archive contains source, fitted model parameters, a pinned environment, entry points, '
      'evidence and verification reports. Raw data, API keys, the research virtual environment and '
      'NOAA-derived experiments are excluded. The package manifest provides per-file checksums. '
      'Joblib files must be loaded only from this trusted package. Outputs refuse CSV overwrites, '
      'and original submissions remain unchanged. No automatic Kaggle operation is implemented.')
    p('Closeout checklist','Heading2')
    p('Before sponsor delivery, the entrant must confirm the OSI license and team information, '
      'complete the private result once known, and check organizer-specific presentation or '
      'documentation requirements. Technical verification does not certify legal eligibility. '
      'The code license does not replace the competition data terms or third-party licenses.')
    p('References and attribution','Heading2')
    p('Kaggle Winning Model Documentation Guidelines: '
      '<link href="https://www.kaggle.com/WinningModelDocumentationGuidelines">kaggle.com/WinningModelDocumentationGuidelines</link>. '
      'Competition rules supplied by the entrant, including the winner source-code and documentation obligation. '
      'Model methods and evidence: source files, frozen protocols and generation metadata in this package.')
    p('Contains modified Copernicus Climate Change Service information 2026. Neither the '
      'European Commission nor ECMWF is responsible for any use that may be made of the '
      'Copernicus information or data it contains.')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#555555'))
        canvas.drawString(60,31,'WORCAP 2026 | S11 technical delivery'); canvas.drawRightString(A4[0]-60,31,str(doc.page))
    SimpleDocTemplate(str(dest),pagesize=A4,rightMargin=60,leftMargin=60,topMargin=48,bottomMargin=50,
                      title='S11 precipitation forecasting technical summary',author='WORCAP competition entrant').build(story,onFirstPage=footer,onLaterPages=footer)
    shutil.copyfile(dest,DELIVERY/'MODEL_SUMMARY.pdf')
    print(dest)


if __name__=='__main__': main()
