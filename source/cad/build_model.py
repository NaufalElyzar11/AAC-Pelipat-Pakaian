"""Accessible folding board: BREP parts, STEP assemblies, OBJ, STL and 3MF.

Rev B prototype; units mm. Run with Python3.12 and the project .cad_runtime.
No slicer machine profile or G-code is generated.
"""
from pathlib import Path
import sys, os, json, math, csv, zipfile, io, time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cad_runtime'))
os.environ.setdefault('EZDXF_CACHE_DIR', str(ROOT / '.cad_runtime' / 'cache'))
import cadquery as cq
import numpy as np
import trimesh
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace

OUT=ROOT/'output'/'cad_rev_b'
for d in ['step','obj','stl','3mf','tests','source']:(OUT/d).mkdir(parents=True,exist_ok=True)
TOP, PLATE_BOTTOM, AXIS = 8., 4., 15.
PIVOTS={'left':{'point':[210,0,AXIS],'axis':[0,1,0],'sign':1},'right':{'point':[420,0,AXIS],'axis':[0,1,0],'sign':-1},'bottom':{'point':[0,270,AXIS],'axis':[1,0,0],'sign':1}}
PARTS={}; INST=[]; REPORT=[]
BLUE=[.12,.38,.65]; ORANGE=[.95,.42,.07]; GRAY=[.20,.23,.27]; METAL=[.64,.66,.68]

def log(t): print(t,flush=True)
def box(w,h,t,x=0,y=0,z=0):return cq.Solid.makeBox(w,h,t,cq.Vector(x,y,z))
def cyl(r,h,x,y,z,axis=(0,0,1)):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),cq.Vector(*axis))
def rounded(w,h,t,r=2,x=0,y=0,z=0):
    return cq.Workplane('XY').box(w,h,t,centered=(False,False,False)).edges('|Z').fillet(r).val().translate((x,y,z))
def fuse(items):return items[0].fuse(*items[1:]).clean() if len(items)>1 else items[0]
def cut(shape,items):return shape.cut(*items).clean() if items else shape
def mesh(shape,tol=.13):
    v,f=shape.tessellate(tol,.16)
    m=trimesh.Trimesh(np.array([[p.x,p.y,p.z] for p in v]),np.asarray(f),process=True)
    # OCC sphere poles can contain zero-area triangles; weld common seams and
    # remove those triangles before writing a manufacturing mesh.
    m.merge_vertices(digits_vertex=7)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.fix_normals();return m
def normalized(shape):
    b=shape.BoundingBox();return shape.translate((-b.xmin,-b.ymin,-b.zmin))
def add_part(name,shape,category='print',orient='same',note=''):
    shape=shape.clean()
    if not shape.isValid() or len(shape.Solids())!=1:raise ValueError(f'{name}: invalid or disconnected BREP, solids={len(shape.Solids())}')
    printable=shape
    if orient=='face_down':printable=shape.rotate((0,0,0),(1,0,0),180)
    elif orient=='hinge_vertical':printable=shape.rotate((0,0,0),(1,0,0),90)
    printable=normalized(printable)
    PARTS[name]={'shape':shape,'print':printable,'category':category,'note':note,'orient':orient}
    return name
def instance(name,part,group='fixed',translation=(0,0,0),rz=0,mirror=False,color=None):
    sh=PARTS[part]['shape']
    if mirror:sh=sh.mirror('YZ')
    if rz:sh=sh.rotate((0,0,0),(0,0,1),rz)
    sh=sh.translate(translation)
    INST.append({'name':name,'part':part,'group':group,'shape':sh,'color':color or (ORANGE if 'marker' in part else BLUE)})
    return sh
def hclear(x,y):return cyl(1.7,14,x,y,-2)
def sink(x,y,top=TOP):return cq.Solid.makeCone(1.7,3.3,1.6,cq.Vector(x,y,top-1.6))
def hex_pocket(x,y,z,depth,af=5.8):
    r=af/math.sqrt(3)
    pts=[(x+r*math.cos(math.radians(a)),y+r*math.sin(math.radians(a))) for a in range(0,360,60)]
    return cq.Workplane('XY').polyline(pts).close().extrude(depth).val().translate((0,0,z))


# Six bolt-on hinge units, axes within nominal630x540 envelope.
# Canonical fixed leaf +X, moving leaf -X, hinge axis+Y atx0,zAXIS.
HINGES=[('L1','left',210,0,0,False),('L2','left',210,190,0,False),
        ('R1','right',420,0,0,True),('R2','right',420,190,0,True),
        ('B1','bottom',238,270,-90,False),('B2','bottom',348,270,-90,False)]
MOUNTS={g:[] for g in ['fixed','left','right','bottom']}
def point_transform(x,y,tx,ty,rz,mir):
    if mir:x=-x
    a=math.radians(rz);return(tx+x*math.cos(a)-y*math.sin(a),ty+x*math.sin(a)+y*math.cos(a))
for tag,g,tx,ty,rz,mir in HINGES:
    for sign,group in [(1,'fixed'),(-1,g)]:
        for yy in [9.,27.]:MOUNTS[group].append(point_transform(sign*18,yy,tx,ty,rz,mir))

PANELS=[('L','left',0,206,0,540,[135,270,405],True),
        ('R','right',424,630,0,540,[135,270,405],True),
        ('F','fixed',214,416,0,266,[135],False),
        ('B','bottom',214,416,274,540,[405],True)]
for prefix,group,x0,x1,y0,y1,seams,perforated in PANELS:
    bounds=[y0]+seams+[y1];w=x1-x0
    for row in range(len(bounds)-1):
        lo=bounds[row]+(.2 if row else 0);hi=bounds[row+1]-(.2 if row<len(bounds)-2 else 0);h=hi-lo
        sh=rounded(w,h,4,2,z=4)
        frame=rounded(w-4,h-4,4,1,x=2,y=2).cut(box(w-12,h-12,6,6,6,-1))
        ribs=[frame]
        for xx in [w*.4,w*.6]:ribs.append(box(3,h-12,4,xx-1.5,6))
        for yy in [h*.375,h*.625]:ribs.append(box(w-12,3,4,6,yy-1.5))
        ribs=fuse(ribs)
        boltpoints=[];pockets=[]
        for seam in seams:
            for yy in [seam-18,seam+18]:
                if lo<yy<hi:
                    for xx in [36,w-36]:boltpoints.append((xx,yy-lo,'splice'))
            if abs(lo-seam)<1:
                for xx in [36,w-36]:pockets.append(box(19,29,6,xx-9.5,-.1,-1))
            if abs(hi-seam)<1:
                for xx in [36,w-36]:pockets.append(box(19,29,6,xx-9.5,h-28.9,-1))
        # Additional counterbored holes reserved for the collar marker.
        for xx,yy in MOUNTS[group]:
            if x0<xx<x1 and lo<yy<hi:boltpoints.append((xx-x0,yy-lo,'hinge'))
        if prefix=='F' and row==0:
            for xx in [303,327]:boltpoints.append((xx-x0,8-lo,'marker'))
        sh=fuse([sh,cut(ribs,pockets)])
        cutters=[]
        for xx,yy,typ in boltpoints:
            cutters.append(hclear(xx,yy))
            if typ=='splice':cutters.append(sink(xx,yy))
        if perforated:
            for xx in np.linspace(26,w-26,5):
                for yy in [h*.25,h*.5,h*.75]:
                    if any(math.hypot(xx-bx,yy-by)<21 for bx,by,_ in boltpoints):continue
                    gy=yy+lo
                    if row==len(bounds)-2 and abs(gy-522)<25 and abs(xx-w/2)<39:continue
                    cutters.append(cyl(12,12,xx,yy,-1))
        # Free-edge finger grip on the last tile of each moving panel.
        if group!='fixed' and row==len(bounds)-2:
            grip=rounded(52,12,12,5.8,x=w/2-26,y=522-lo-6,z=-1)
            cutters.append(grip)
        sh=cut(sh,cutters)
        pn=f'panel_{prefix}{row+1}'
        add_part(pn,sh,orient='face_down',note=f'Panel {group}, row{row+1}; installed topz8; print clothface down')
        instance(pn,pn,group,(x0,lo,0))
    for j,seam in enumerate(seams):
        for k,xx in enumerate([36,w-36]):
            # Strap rests beneath panel; all mount holes align in worldspace.
            if 'splice_strap' not in PARTS:
                st=rounded(18,56,4,2,x=-9,y=-28)
                st=cut(st,[hclear(0,-18),hclear(0,18),hex_pocket(0,-18,-.1,2.7),hex_pocket(0,18,-.1,2.7)])
                add_part('splice_strap',st,orient='face_down',note='16 copies; captive M3 nut pockets face underside')
            instance(f'splice_{prefix}_{j+1}_{k+1}','splice_strap',group,(x0+xx,seam,0),color=GRAY)
    log(f'Panels {prefix} complete')


def hinge_half(positive=True,bore=4.4):
    foot=rounded(20,36,3,1,x=8,y=0,z=TOP)
    segs=[(9.3,8.4),(27.3,8.7)] if positive else [(0,8.7),(18.3,8.4)]
    bits=[foot]
    for start,length in segs:
        bits.append(cyl(4.5,length,0,start,AXIS,(0,1,0)))
        bits.append(box(10,length,AXIS-TOP,0,start,TOP))
    sh=fuse(bits)
    sh=cut(sh,[cyl(bore/2,40,0,-2,AXIS,(0,1,0)),
               cyl(1.7,8,18,9,TOP-1),cyl(1.7,8,18,27,TOP-1),sink(18,9,TOP+3),sink(18,27,TOP+3)])
    if not positive:sh=sh.mirror('YZ')
    return sh
add_part('hinge_A',hinge_half(True),orient='hinge_vertical',note='6 copies; +Xleaf; supports and brim REQUIRED below knuckle ledges')
add_part('hinge_B',hinge_half(False),orient='hinge_vertical',note='6 copies; -Xleaf; supports and brim REQUIRED; magnet drive not included')
add_part('metal_pin_reference',cyl(2,40,0,-2,AXIS,(0,1,0)),category='reference',note='Do not print: 4mm metal hinge pin, candidate cut length40mm')
for tag,g,tx,ty,rz,mir in HINGES:
    # Right side swaps A/B roles instead of mirroring printable geometry.
    # Every installed leaf now matches one of the two supplied print files.
    instance(tag+'_fixed','hinge_B' if mir else 'hinge_A','fixed',(tx,ty,0),rz,False,color=GRAY)
    instance(tag+'_moving','hinge_A' if mir else 'hinge_B',g,(tx,ty,0),rz,False,color=GRAY)
    instance(tag+'_pin','metal_pin_reference','reference',(tx,ty,0),rz,False,color=METAL)
log('Hinges complete')

# Low tactile markers, removable collar locator, and adhesive side index tabs.
mk=rounded(46,38,2,3,x=-23,y=-20,z=TOP)
mk=fuse([mk,rounded(40,5,4,2,x=-20,y=-13,z=TOP+2)])
mk=cut(mk,[cyl(1.7,8,-12,8,TOP-1),cyl(1.7,8,12,8,TOP-1),sink(-12,8,TOP+2),sink(12,8,TOP+2)])
add_part('marker_collar',mk,note='Mount with2M3; raised stop outside y0 boundary')
instance('collar_stop','marker_collar','fixed',(315,0,0),color=ORANGE)
add_part('marker_index',rounded(8,22,1.6,2),note='3 copies; adhesive; no raised wall around board')
instance('left_index','marker_index','left',(2,94,TOP),color=ORANGE)
instance('right_index','marker_index','right',(620,94,TOP),color=ORANGE)
instance('bottom_index','marker_index','bottom',(304,538,TOP),rz=-90,color=ORANGE)

# Separate control housing with standard16mm button holes; electronics fit is generic.
CW,CH=250.,96.
base=rounded(CW,CH,30,7)
inner=rounded(CW-6,CH-6,30,4,x=3,y=3,z=3)
base=base.cut(inner)
posts=[(10,10),(CW-10,10),(10,CH-10),(CW-10,CH-10)]
base=fuse([base]+[cyl(4,27,x,y,3) for x,y in posts])
base=cut(base,[cyl(1.35,31,x,y,0) for x,y in posts])
# Round cable feed-through on rear wall, grommet to be selected after actual cable.
base=base.cut(cyl(4.1,8,225,-2,15,(0,1,0)))
# Universal tie-down slots in bottom for straps, no guessed board mounting pattern.
base=cut(base,[rounded(14,3,6,1,x=x,y=y,z=-1) for x,y in [(70,28),(70,64),(140,28),(140,64),(200,28),(200,64)]])
add_part('control_base',base,note='250x96x30; cablegrommet hole8.2; PCB tie-downs; no verified PCB standoffs')
lid=rounded(CW,CH,3.2,7)
holes=[cyl(8.15,7,x,45,-1) for x in [84,132,180]]+[cyl(3.65,7,222,45,-1)]
holes += [cyl(1.7,7,x,y,-1) for x,y in posts]
holes += [cq.Solid.makeCone(1.7,3.3,1.6,cq.Vector(x,y,1.6)) for x,y in posts]
for xx in np.arange(16,45,5):
    for yy in np.arange(27,65,5):
        if (xx-30)**2+(yy-45)**2<19**2:holes.append(cyl(1.5,7,xx,yy,-1))
# Speaker screw holes for a generic40mm enclosure; optional adhesive cradle instead.
lid=cut(lid,holes)
add_part('control_lid',lid,note='3 holes16.3mm; volumehole7.3; speakergrille; componentmeasurements required')
CP=(190.,595.,0.)
instance('control_base','control_base','control',CP,color=GRAY)
instance('control_lid','control_lid','control',(CP[0],CP[1],30),color=GRAY)

# Uncontracted6-dot Braille labels, replaceable and separate from housing.
BRAILLE={'a':[1],'b':[1,2],'e':[1,5],'g':[1,2,4,5],'i':[2,4],'k':[1,3],'l':[1,2,3],'m':[1,3,4],'n':[1,3,4,5],'r':[1,2,3,5],'u':[1,3,6]}
def braille_plate(word):
    width=(len(word)-1)*6.2+4+6
    sh=rounded(width,12.3,1.6,1.2)
    dots=[]
    for j,ch in enumerate(word):
        for dot in BRAILLE[ch]:
            col=0 if dot<=3 else 1;row=(dot-1)%3
            dots.append(cq.Solid.makeSphere(.75,cq.Vector(3+j*6.2+col*2.4,3.0+row*2.4,1.6)))
    return fuse([sh]+dots),width
for word,x in [('kembali',84),('mulai',132),('ulang',180)]:
    sh,width=braille_plate(word);pn='braille_'+word
    add_part(pn,sh,note='Uncontracted sixdot letters; reader validation required; dotheight0.75mm')
    instance(pn,pn,'control',(CP[0]+x-width/2,CP[1]+73,33.2),color=ORANGE)

# Visual-only standard button envelopes; not printable actuators.
for i,x in enumerate([84,132,180]):
    pn=f'button_reference_{i+1}';sh=cyl(7.7,18,0,0,-14).fuse(cyl(11.5,4,0,0,3.2)).clean()
    add_part(pn,sh,category='reference',note='Buy16mm panelmount pushbutton; visible cap is an envelope')
    instance(pn,pn,'control',(CP[0]+x,CP[1]+45,30),color=ORANGE)
    # Adhesive tactile overlays, not replacement switch mechanisms.
    overlay=cyl(8,1,0,0,0)
    if i==0:
        icon=cq.Workplane('XY').polyline([(-5.8,0),(3.6,-4.6),(3.6,4.6)]).close().extrude(1.3).edges('|Z').fillet(.5).val().translate((0,0,1))
    elif i==1:icon=cyl(6.5,1.3,0,0,1)
    else:icon=cyl(6.7,1.3,0,0,1).cut(cyl(4.2,2,0,0,.8))
    overlay=fuse([overlay,icon]);oname=['button_overlay_back','button_overlay_next','button_overlay_repeat'][i]
    add_part(oname,overlay,note='Adhesive16mm tactile overlay; actual switch cap must provide flat diameter>=16mm')
    instance(oname,oname,'control',(CP[0]+x,CP[1]+45,37.2),color=ORANGE)
add_part('volume_knob_reference',cyl(8.5,14,0,0,0),category='reference',note='Actual knob/shaft not specified')
instance('volume_knob','volume_knob_reference','control',(CP[0]+222,CP[1]+45,33.2),color=GRAY)
log('Control pod and Braille complete')

# Fit tests: make these first, rather than all twelve plates.
coupon=rounded(92,34,8,2)
for x,d in zip([12,34,56,78],[4.2,4.3,4.4,4.5]):coupon=coupon.cut(cyl(d/2,12,x,17,-1))
add_part('TEST_pin_bores_42_43_44_45',coupon,category='test',note='holes lefttoright4.2,4.3,4.4,4.5mm; test actual4mm rod')
for side in ['A','B']:
    sh=rounded(52,38,4,1,z=4)
    yy=20 if side=='A' else 18
    sh=cut(sh,[hclear(26,yy),sink(26,yy)])
    add_part(f'TEST_splice_panel_{side}',sh,category='test',orient='face_down',note='Two smallplates for one actual splice strap; align seam and bolt centres')
# Short dummy panels with same hinge mounts, for turning a physical hinge coupon.
for typ,sign in [('fixed',1),('moving',-1)]:
    sh=rounded(55,44,4,1,x=(4 if sign>0 else -59),y=-4,z=4)
    sh=cut(sh,[cyl(1.7,12,sign*18,y,-1) for y in [9,27]])
    add_part('TEST_hinge_panel_'+typ,sh,category='test',orient='face_down',note='Useone normalhingepair andone4mm pin; completephysicalfoldclearance test')

# A separate generic sensor adapter template; deliberately not installed in model.
adapter=rounded(30,30,3,2)
adapter=adapter.cut(cyl(4.2,8,15,15,-1))
for xx in [5,25]:adapter=adapter.cut(rounded(3,15,8,1,x=xx-1.5,y=7.5,z=-1))
add_part('OPTION_sensor_adapter_template',adapter,category='optional',note='UnverifiedgenericPCB template; NOT a finalized AS5600 mount or magnet drive')

NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
register_namespace('',NS)
def write_3mf(path,m,name):
    # Core3MF, one printable object centred on a260mm bed; explicit millimetres.
    r=Element('{'+NS+'}model',{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    SubElement(r,'{'+NS+'}metadata',{'name':'Title'}).text=name+' - prototype Rev B'
    resources=SubElement(r,'{'+NS+'}resources')
    obj=SubElement(resources,'{'+NS+'}object',{'id':'1','type':'model','name':name})
    me=SubElement(obj,'{'+NS+'}mesh');vs=SubElement(me,'{'+NS+'}vertices');ts=SubElement(me,'{'+NS+'}triangles')
    for v in m.vertices:SubElement(vs,'{'+NS+'}vertex',dict(zip(['x','y','z'],[f'{a:.6f}' for a in v])))
    for f in m.faces:SubElement(ts,'{'+NS+'}triangle',dict(zip(['v1','v2','v3'],map(str,f))))
    build=SubElement(r,'{'+NS+'}build');ext=m.extents
    SubElement(build,'{'+NS+'}item',{'objectid':'1','transform':f'1 0 0 0 1 0 0 0 1 {130-ext[0]/2:.6f} {130-ext[1]/2:.6f} 0'})
    types='<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels);z.writestr('3D/3dmodel.model',tostring(r,encoding='utf-8',xml_declaration=True))

quantities={n:sum(i['part']==n for i in INST) for n in PARTS}
for name,p in PARTS.items():
    if p['category']=='reference':continue
    m=mesh(p['print'])
    if not (m.is_watertight and m.is_winding_consistent and m.volume>0):raise ValueError(f'Meshinvalid:{name}')
    if any(m.extents>np.array([250.1,250.1,250.1])):raise ValueError(f'Partdoesnotfitbed:{name}:{m.extents}')
    folder='tests' if p['category']=='test' else 'stl'
    m.export(OUT/folder/(name+'.stl'))
    write_3mf(OUT/'3mf'/(name+'.3mf'),m,name)
    cq.exporters.export(p['shape'],str(OUT/'step'/(name+'.step')))
    p['mesh_print']=m
    REPORT.append({'part':name,'category':p['category'],'quantity':quantities[name] or 1,'bounds_mm':m.extents.round(3).tolist(),'volume_mm3':round(p['shape'].Volume(),3),'mass_solid_PLA_g':round(p['shape'].Volume()*.00124,2),'watertight':bool(m.is_watertight),'note':p['note']})
log(f'{len(REPORT)} printable/testpart geometries validated and exported')

def posed_shape(item,poses):
    sh=item['shape'];g=item['group']
    if g in PIVOTS and poses.get(g,0):
        p=PIVOTS[g];pt=p['point'];axis=p['axis'];end=[a+b for a,b in zip(pt,axis)]
        sh=sh.rotate(tuple(pt),tuple(end),poses[g]*p['sign'])
    return sh
def assembly(poses,name):
    a=cq.Assembly(name=name)
    for it in INST:a.add(posed_shape(it,poses),name=it['name'],color=cq.Color(*it['color']))
    return a
for label,poses in [('assembly_open',{}),('pose_left_90',{'left':90}),('pose_right_90',{'right':90}),('pose_bottom_90',{'bottom':90})]:
    a=assembly(poses,label)
    a.export(str(OUT/'step'/(label+'.step')))
    log('STEP '+label)

# OBJ with namedobjects/materials; no animation or joints are encoded in OBJ.
obj=['# FoldingboardRevB;unitsmillimeters; objectsseparate; seejoint_axes.json'];mtl=[];offset=0;viewer=[]
obj.append('mtllib assembly_open.mtl')
for i,it in enumerate(INST):
    m=mesh(it['shape']);col=it['color']
    obj+=['o '+it['name'],'usemtl material_'+str(i)]
    obj += [f'v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}' for v in m.vertices]
    obj += [f'f {f[0]+offset+1} {f[1]+offset+1} {f[2]+offset+1}' for f in m.faces]
    mtl += [f'newmtl material_{i}',f'Kd {col[0]} {col[1]} {col[2]}','Ka 0.15 0.15 0.15','Ks 0.1 0.1 0.1','']
    offset+=len(m.vertices)
    viewer.append({'name':it['name'],'group':it['group'],'vertices':m.vertices.round(4).tolist(),'faces':m.faces.tolist(),'color':col})
(OUT/'obj'/'assembly_open.obj').write_text('\n'.join(obj),encoding='utf-8')
(OUT/'obj'/'assembly_open.mtl').write_text('\n'.join(mtl),encoding='utf-8')
(OUT/'source'/'joint_axes.json').write_text(json.dumps(PIVOTS,indent=2),encoding='utf-8')
data={'meshes':viewer,'pivots':PIVOTS}
(OUT/'source'/'model_preview_data.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
template=(ROOT/'cad'/'preview_template.html').read_text(encoding='utf-8')
(OUT/'COBA_MEKANISME.html').write_text(template.replace('__MODEL_DATA__',json.dumps(data,separators=(',',':'))),encoding='utf-8')
(OUT/'parts_manifest.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
with (OUT/'parts_manifest.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['part','category','quantity','bounds_mm','volume_mm3','mass_solid_PLA_g','watertight','note']);writer.writeheader();writer.writerows(REPORT)

# Collision test aggregates moving groups. Pins and control are not moving parts.
moving={g:cq.Compound.makeCompound([i['shape'] for i in INST if i['group']==g]) for g in PIVOTS}
collision=[]
for g in PIVOTS:
    target=cq.Compound.makeCompound([i['shape'] for i in INST if i['group'] not in [g,'control','reference']])
    # Test one panel at a time; intended workflow folds and reopens before next panel.
    for deg in range(0,181,15):
        p=PIVOTS[g];end=[a+b for a,b in zip(p['point'],p['axis'])]
        sh=moving[g].rotate(tuple(p['point']),tuple(end),deg*p['sign']) if deg else moving[g]
        inter=sh.intersect(target);vol=sum(s.Volume() for s in inter.Solids())
        collision.append({'panel':g,'angle_deg':deg,'intersection_mm3':round(vol,6)})
        if vol>.1:log(f'COLLISION {g}@{deg}: {vol:.3f}mm3')
(OUT/'collision_report.json').write_text(json.dumps(collision,indent=2),encoding='utf-8')
mass=sum(r['mass_solid_PLA_g']*r['quantity'] for r in REPORT if r['category']=='print')
summary={'revision':'B','units':'mm','open_board_nominal_mm':[630,540],'top_surface_z_mm':TOP,'pivot_z_mm':AXIS,'unique_printable_and_test_parts':len(REPORT),'installed_printable_count':sum(quantities[n] for n,p in PARTS.items() if p['category']=='print'),'solid_PLA_mass_all_installed_g':round(mass,1),'max_sampled_collision_mm3':max(c['intersection_mm3'] for c in collision),'collision_angle_samples':len(collision),'printable_meshes_watertight':all(r['watertight'] for r in REPORT),'sensor_mount_status':'Genericadapteronly; finalPCBmount and keyedmagnetcarrier notincluded','electronics_housing_status':'Generic16mmbutton holes and tiedownslots; actualcomponents notmeasured'}
(OUT/'validation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
log(json.dumps(summary,indent=2))
