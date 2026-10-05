// Cópia do CSS_LAUDO do protocolo fixo (formulario-novo-paciente.html), para
// o relatório dos modelos de protocolo sair com o mesmo visual — e com as
// mesmas classes que app/services/laudo_documento.py converte para Word.
// Mudou lá, replique aqui.
export const CSS_LAUDO = `
@page{size:A4;margin:30mm 20mm 27mm 20mm;
  @top-center{content:element(cabecalhoPagina);vertical-align:bottom;padding-bottom:4mm}
  @bottom-center{content:element(rodapePagina);vertical-align:top;padding-top:1mm}}
@page capa{margin:0;@top-center{content:none}@bottom-center{content:none}}
.capa{page:capa;width:210mm;height:297mm;margin:0;padding:0;overflow:hidden;break-after:page;page-break-after:always}
.capa img{display:block;width:210mm;height:297mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff}
body{font-family:Arial,"Liberation Sans",Helvetica,FreeSans,"DejaVu Sans",sans-serif;font-size:10pt;line-height:1.5;color:#000}
.moldura{position:fixed;top:-21.5mm;bottom:-18.5mm;left:-11.5mm;right:-11.5mm;border:.75pt solid #000}
.cabecalho-pagina{position:running(cabecalhoPagina);text-align:center}
.cabecalho-pagina img{width:19mm}
.rodape-pagina{position:running(rodapePagina);text-align:center}
.rodape-pagina img{width:78mm}
p{margin:0 0 6pt;text-align:justify;orphans:2;widows:2}
p.recuo{text-indent:12.5mm}
p.centro{text-align:center}
p.direita{text-align:right}
p.compacto{margin:0;line-height:1.25}
mark{color:#000;padding:0 1pt}
mark.cinza{background:#d9d9d9}
mark.amarelo{background:#ffff00}
.faixa{background:#bfbfbf;font-weight:bold;padding:1mm 2mm;margin:5mm 0 3mm;line-height:1.45}
.faixa.centro{text-align:center}
.faixa-topico{background:#a6a6a6;font-weight:bold;font-size:9.5pt;padding:1mm 2mm;margin:4mm 0 3mm;break-after:avoid;page-break-after:avoid}
h2{font-size:12.5pt;text-align:center;margin:3mm 0 5mm;break-after:avoid;page-break-after:avoid}
h2.roxo{color:#5b4a91}
h2.marcado{font-size:10pt;margin:5mm 0 3mm}
h3{font-size:10pt;margin:5mm 0 2mm;break-after:avoid;page-break-after:avoid}
ul{list-style:none;margin:0 0 7pt;padding:0}
ul li{position:relative;line-height:1.5}
ul.bullets li{padding-left:12mm}
ul.bullets li:before{content:"•";position:absolute;left:5mm}
ul.checks li{padding-left:6mm}
ul.checks li:before{content:"✔";position:absolute;left:0}
table{border-collapse:collapse;width:100%;margin:0 0 5mm}
tr{break-inside:avoid;page-break-inside:avoid}
table.tabela td,table.tabela th{padding:1.2mm 1.6mm;vertical-align:middle;line-height:1.2}
table.tabela th{font-weight:bold;text-align:center}
table.dupla{border:2.5px double #000}
table.dupla td,table.dupla th{border:2.5px double #000}
table.compacta td,table.compacta th{padding:.5mm 1.4mm;line-height:1.15}
table.quadro td,table.quadro th{padding:.7mm 1.2mm;line-height:1.12}
h2.marcado{margin:3mm 0 2mm}
table.simples td,table.simples th{border:.75pt solid #000}
table.roxa td,table.roxa th{border:.75pt solid #b4a7d6}
table.centro td{text-align:center}
.grafico{text-align:center;margin:3mm 0 4mm;break-inside:avoid;page-break-inside:avoid}
.grafico img,.graficos-lado img,.fotos img,.cab-foto img{display:inline-block;vertical-align:middle}
.graficos-lado{text-align:center;margin:3mm 0 5mm;break-inside:avoid}
.graficos-lado img{margin:0 2mm}
.fotos{text-align:center;margin:10mm 0 4mm;break-inside:avoid}
.fotos img{margin:0 5mm}
table.cab-paciente{margin:0 0 3mm}
table.cab-paciente td{vertical-align:middle;padding:0}
td.cab-foto{width:48mm}
td.cab-espaco{width:8mm}
.cab-box{border:.75pt solid #000;padding:5mm 3mm}
.cab-box p{text-align:center;font-weight:bold;margin:2.2mm 0;line-height:1.25;font-size:10.5pt}
.caixa-cinza{background:#a6a6a6;padding:3mm 4mm;margin:4mm 0;font-weight:bold}
.caixa-cinza.clara{background:#bfbfbf}
.caixa-cinza p{margin:0 0 3pt}
.linha-assinatura{border-top:.75pt solid #000;width:95mm;margin:16mm auto 1mm}
.assinatura-nome{font-family:"Arial Narrow","Liberation Sans Narrow",Arial,sans-serif;font-style:italic;font-size:15pt}
.quebra{break-before:page;page-break-before:always;height:0;margin:0}
@media screen{
  body{background:#e7e7ee;padding:14px 0}
  .moldura,.rodape-pagina{display:none}
  .cabecalho-pagina{background:#fff;max-width:210mm;margin:0 auto;padding-top:8mm}
  .documento{background:#fff;max-width:210mm;margin:0 auto;padding:6mm 20mm 14mm;box-shadow:0 2px 10px rgba(0,0,0,.15)}
  .quebra{border-top:2px dashed #c9c3ee;margin:8mm -20mm}
  .capa{width:auto;height:auto;max-width:210mm;margin:0 auto 14px;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.15)}
  .capa img{width:100%;height:auto}
}`
