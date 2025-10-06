import io
import fitz
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from typing import List
from PIL import Image

app = FastAPI()

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'/>
  <title>PDF Field Placer</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 1rem; }
    #canvasWrapper { position: relative; display: inline-block; }
    #pdfImage { border: 1px solid #666; }
    .field-box { position:absolute; border:1px solid red; font-size:10px; background:rgba(255,0,0,0.1); }
#corgi { position:fixed; top:4px; left:0; font-size:28px; pointer-events:none; display:none; z-index:1000; }
    #fieldsList { margin-top:1rem; }
    #controls { margin:1rem 0; }
    #fieldsList table { border-collapse: collapse; }
    #fieldsList th, #fieldsList td { border:1px solid #ccc; padding:4px 6px; }
    .small { width:80px; }
  </style>
</head>
<body>
  <div id="corgi">🐕‍🦺</div>
  <h1>PDF Field Placer (First Page)</h1>
  <form id="uploadForm">
    <input type="file" id="pdfInput" name="pdf" accept="application/pdf" required />
    <button type="submit" style="display:none;">Upload</button>
  </form>
  <div id="controls" style="display:none;">
    <button id="downloadBtn">Download Filled PDF</button>
    <button id="undoBtn" type="button">Undo Last</button>
    <button id="clearBtn" type="button">Clear Fields</button>
    <button id="exportBtn" type="button">Export JSON</button>
    <label style="display:inline-block;">Import JSON <input type="file" id="importJson" accept="application/json" style="width:160px;"></label>
    <button id="corgiBtn" type="button" title="Release the corgi">🐕</button>
  </div>
  <div id="canvasWrapper"></div>
  <div id="fieldsList" style="display:none;">
    <h3>Fields</h3>
    <table id="fieldsTable">
      <thead><tr><th>#</th><th>Name</th><th>X</th><th>Y</th><th>W</th><th>H</th><th>Remove</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
<script>
let imageNaturalWidth = 0;
let imageNaturalHeight = 0;
let scaleX = 1;
let scaleY = 1;
let fields = [];
let pdfId = null;

const uploadForm = document.getElementById('uploadForm');
const canvasWrapper = document.getElementById('canvasWrapper');
const controls = document.getElementById('controls');
const fieldsList = document.getElementById('fieldsList');
const fieldsTableBody = document.querySelector('#fieldsTable tbody');
const downloadBtn = document.getElementById('downloadBtn');
const undoBtn = document.getElementById('undoBtn');
const clearBtn = document.getElementById('clearBtn');
const exportBtn = document.getElementById('exportBtn');
const importJson = document.getElementById('importJson');
const corgiBtn = document.getElementById('corgiBtn');
const corgiEl = document.getElementById('corgi');
let corgiTimer = null;

async function doUpload(){
  const formData = new FormData(uploadForm);
  const res = await fetch('/upload', { method: 'POST', body: formData });
  if (!res.ok) { alert('Upload failed'); return; }
  const data = await res.json();
  pdfId = data.id;
  const img = new Image();
  img.id = 'pdfImage';
  img.onload = () => {
    imageNaturalWidth = img.naturalWidth;
    imageNaturalHeight = img.naturalHeight;
    canvasWrapper.innerHTML = '';
    canvasWrapper.appendChild(img);
    controls.style.display='block';
    fieldsList.style.display='block';
    fields = [];
    refreshFields();
  };
  img.src = data.image_url;
}

const pdfInput = document.getElementById('pdfInput');
pdfInput.addEventListener('change', ()=>{ if(pdfInput.files.length) { doUpload(); }});
uploadForm.addEventListener('submit', (e)=>{ e.preventDefault(); });

function refreshFields(){
  // remove existing overlay boxes
  document.querySelectorAll('.field-box').forEach(n=>n.remove());
  fieldsTableBody.innerHTML='';
  const img = document.getElementById('pdfImage');
  if (!img) return;
  scaleX = imageNaturalWidth / img.clientWidth;
  scaleY = imageNaturalHeight / img.clientHeight;
  fields.forEach((f,i)=>{
    const div = document.createElement('div');
    div.className='field-box';
    div.style.left = (f.x/scaleX) + 'px';
    div.style.top = (f.y/scaleY) + 'px';
    div.style.width = (f.w/scaleX) + 'px';
    div.style.height = (f.h/scaleY) + 'px';
    div.textContent = f.name;
    canvasWrapper.appendChild(div);
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${i+1}</td><td><input class="fname" data-i="${i}" value="${f.name}" style="width:120px" /></td><td>${f.x.toFixed(1)}</td><td>${f.y.toFixed(1)}</td><td>${f.w}</td><td>${f.h}</td><td><button data-i="${i}" class="rm">X</button></td>`;
    fieldsTableBody.appendChild(tr);
  });
  document.querySelectorAll('.rm').forEach(btn=>btn.addEventListener('click', (e)=>{
    const idx = parseInt(e.target.getAttribute('data-i'));
    fields.splice(idx,1);
    refreshFields();
  }));
  document.querySelectorAll('.fname').forEach(inp=>inp.addEventListener('input', (e)=>{
    const idx = parseInt(e.target.getAttribute('data-i'));
    fields[idx].name = e.target.value;
  }));
}

canvasWrapper.addEventListener('click', (e)=>{
  const img = document.getElementById('pdfImage');
  if(!img) return;
  const rect = img.getBoundingClientRect();
  const clickX = (e.clientX - rect.left) * scaleX;
  const clickY = (e.clientY - rect.top) * scaleY;
  const name = 'Field_' + (fields.length+1);
  const width = 180; const height = 16;
  // Left edge at clickX; vertical center at clickY
  const leftX = clickX;
  const topY = clickY - height/2;
  fields.push({name:name, x:leftX, y:topY, w:width, h:height});
  refreshFields();
});

downloadBtn.addEventListener('click', async ()=>{
  if(!pdfId){ alert('No PDF loaded'); return; }
  const res = await fetch('/build', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id:pdfId, fields:fields})});
  if(!res.ok){ alert('Build failed'); return; }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'fillable.pdf';
  a.click();
});

undoBtn.addEventListener('click', ()=>{ fields.pop(); refreshFields(); });
clearBtn.addEventListener('click', ()=>{ fields=[]; refreshFields(); });
exportBtn.addEventListener('click', ()=>{
  const dataStr = JSON.stringify(fields, null, 2);
  const blob = new Blob([dataStr], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'fields.json';
  a.click();
});
importJson.addEventListener('change', ()=>{
  if(importJson.files.length===0) return;
  const file = importJson.files[0];
  const reader = new FileReader();
  reader.onload = (ev)=>{
    try {
      const arr = JSON.parse(ev.target.result);
      if(Array.isArray(arr)){
        fields = arr.filter(f=>f && typeof f==='object' && 'x' in f && 'y' in f && 'w' in f && 'h' in f && 'name' in f);
        refreshFields();
      } else {
        alert('Invalid JSON format');
      }
    } catch(e){ alert('Failed to parse JSON'); }
  };
  reader.readAsText(file);
});

function startCorgi(){
  if(corgiTimer){ return; }
  corgiEl.style.display='block';
  let pos = -60;
  const speed = 2; // px per frame
  const step = ()=>{
    pos += speed;
    corgiEl.style.left = pos + 'px';
    if(pos > window.innerWidth){
       pos = -60; // loop
    }
    corgiTimer = requestAnimationFrame(step);
  };
  corgiTimer = requestAnimationFrame(step);
}

corgiBtn.addEventListener('click', startCorgi);
</script>
</body>
</html>
"""

# In-memory storage for simplicity (not production-safe)
PDF_STORE = {}
IMAGE_STORE = {}

@app.post('/upload')
async def upload_pdf(pdf: UploadFile = File(...)):
    content = await pdf.read()
    doc = fitz.open(stream=content, filetype='pdf')
    page = doc[0]
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    pdf_id = str(id(content))
    PDF_STORE[pdf_id] = content
    IMAGE_STORE[pdf_id] = buf.getvalue()
    return JSONResponse({"id": pdf_id, "image_url": f"/image/{pdf_id}"})

@app.get('/image/{pdf_id}')
async def get_image(pdf_id: str):
    data = IMAGE_STORE.get(pdf_id)
    if not data:
        return JSONResponse({"error": "not found"}, status_code=404)
    return StreamingResponse(io.BytesIO(data), media_type='image/png')

@app.post('/build')
async def build_pdf(payload: dict):
    pdf_id = payload.get('id')
    fields = payload.get('fields', [])
    raw = PDF_STORE.get(pdf_id)
    if raw is None:
        return JSONResponse({"error":"invalid id"}, status_code=400)
    doc = fitz.open(stream=raw, filetype='pdf')
    page = doc[0]
    for f in fields:
        # fields stored with PDF coordinate system derived from rendered image at zoom 2.0; we used raw PDF units directly because scaleX uses natural sizes.
        x = f['x']/2.0  # reverse zoom (since we captured coords after scaleX multiply)
        y = f['y']/2.0
        w = f['w']/2.0
        h = f['h']/2.0
        rect = fitz.Rect(x, y, x+w, y+h)
        widget = fitz.Widget()
        widget.rect = rect
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        widget.field_name = f['name']
        widget.text_font = "Helv"
        widget.text_fontsize = 9
        page.add_widget(widget)
    out_buf = io.BytesIO()
    doc.save(out_buf, garbage=4, deflate=True, clean=True)
    doc.close()
    out_buf.seek(0)
    return StreamingResponse(out_buf, media_type='application/pdf', headers={'Content-Disposition':'attachment; filename="fillable.pdf"'})

@app.get('/')
async def index():
    return HTMLResponse(HTML_PAGE)
