import csv
import sys
import tkinter as tk
from collections import defaultdict

PATH = sys.argv[1] if len(sys.argv) > 1 else 'olsr-route-trace.csv'
frames = defaultdict(lambda: {'nodes': {}, 'edges': [], 'mpr': [], 'routes': {}})
tx, rx = defaultdict(list), defaultdict(set)
with open(PATH, newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        t = round(float(r['time']), 3)
        kind = r['type']
        i = int(r['id'])
        if kind == 'NODE':
            frames[t]['nodes'][i] = (float(r['x_or_to']), float(r['y_or_weight']), float(r['hello_or_unused']))
        elif kind == 'EDGE':
            frames[t]['edges'].append((i, int(float(r['x_or_to'])), float(r['y_or_weight'])))
        elif kind == 'MPR':
            frames[t]['mpr'].append((i, int(float(r['x_or_to']))))
        elif kind == 'ROUTE':
            frames[t]['routes'][(i, int(float(r['x_or_to'])))] = (int(float(r['y_or_weight'])), int(float(r['hello_or_unused'])))
        elif kind == 'TX':
            tx[(i, int(float(r['x_or_to'])))].append((t, int(float(r['y_or_weight'])), int(float(r['hello_or_unused']))))
        elif kind == 'RX':
            rx[(int(float(r['x_or_to'])), i)].add((t, int(float(r['y_or_weight']))))
times = sorted(t for t, frame in frames.items() if frame['nodes'])
if not times:
    raise SystemExit('No NODE frames found. Run ./ns3 run "scratch/olsr-route-visual-allpairs" first.')
node_ids = sorted(frames[times[0]]['nodes'])

root = tk.Tk()
root.title('OLSR actual routing / MPR explorer')
root.geometry('1450x950')
try: root.state('zoomed')
except tk.TclError: pass
root.configure(bg='#edf2f7')
index = tk.IntVar(value=0)
source = tk.IntVar(value=3 if 3 in node_ids else node_ids[0])
dest = tk.IntVar(value=0 if 0 in node_ids else node_ids[-1])
selected = tk.IntVar(value=-1)
playing = tk.BooleanVar(value=False)
speed = tk.DoubleVar(value=1.0)  # Playback multiplier (0.25x to 4x)
show_physical = tk.BooleanVar(value=True)
show_mpr = tk.BooleanVar(value=True)
header = tk.Frame(root, bg='#edf2f7'); header.pack(fill='x', padx=14, pady=8)
tk.Label(header, text='OLSR 실제 라우팅 경로 · MPR 분석', bg='#edf2f7', fg='#17243a', font=('NanumGothic', 17, 'bold')).pack(side='left')
summary = tk.Label(header, bg='#edf2f7', fg='#465569', font=('Arial', 11)); summary.pack(side='right')
body = tk.Frame(root, bg='#edf2f7'); body.pack(fill='both', expand=True, padx=12)
canvas = tk.Canvas(body, bg='white', highlightthickness=0); canvas.pack(side='left', fill='both', expand=True)
side = tk.Frame(body, bg='white', width=365); side.pack(side='right', fill='y', padx=(8,0)); side.pack_propagate(False)
tk.Label(side, text='경로 및 패킷 분석', bg='white', font=('NanumGothic', 16, 'bold')).pack(fill='x', padx=12, pady=12)
detail = tk.Text(side, font=('NanumGothic', 11), bg='white', fg='#263445', wrap='word', relief='flat', padx=12)
detail.pack(fill='both', expand=True)
bar = tk.Frame(root, bg='#edf2f7'); bar.pack(fill='x', padx=12, pady=8)

hitboxes=[]
def xy(x,y):
    cw,ch=max(canvas.winfo_width(),300),max(canvas.winfo_height(),200)
    s=min((cw-80)/600,(ch-80)/400)
    return (cw-600*s)/2+x*s,(ch-400*s)/2+y*s

def resolve_path(routes, src, dst, count):
    if src == dst: return [src], 'same node'
    path=[src]
    for _ in range(count):
        entry=routes.get((path[-1],dst))
        if entry is None: return path, 'no route entry at node ' + str(path[-1])
        nxt=entry[0]
        if nxt in path: return path+[nxt], 'routing loop detected'
        path.append(nxt)
        if nxt==dst: return path, 'route found'
    return path, 'hop limit exceeded'

def draw(*_):
    k=max(0,min(index.get(),len(times)-1)); t=times[k]; frame=frames[t]
    pos=frame['nodes']; routes=frame['routes']; src=source.get(); dst=dest.get()
    path,status=resolve_path(routes,src,dst,len(pos))
    edges=set(tuple(sorted((i,j))) for i,j,_ in frame['edges'] if i in pos and j in pos and i!=j)
    mprs=set(frame['mpr'])
    canvas.delete('all');hitboxes.clear()
    x1,y1=xy(0,0);x2,y2=xy(600,400)
    canvas.create_rectangle(x1,y1,x2,y2,outline='#bac9dc',width=2)
    if show_physical.get():
        for i,j in edges:
            a,b=xy(*pos[i][:2]),xy(*pos[j][:2]);canvas.create_line(*a,*b,fill='#dce5ef',width=1)
    if show_mpr.get():
        for i,j in mprs:
            if i in pos and j in pos:
                canvas.create_line(*xy(*pos[i][:2]),*xy(*pos[j][:2]),fill='#16a34a',width=2,dash=(5,4))
    if status=='route found':
        for i,j in zip(path,path[1:]):
            if i in pos and j in pos:
                canvas.create_line(*xy(*pos[i][:2]),*xy(*pos[j][:2]),fill='#e11d48',width=5,arrow=tk.LAST,arrowshape=(13,15,5))
    for i,(x,y,_) in pos.items():
        px,py=xy(x,y)
        color=('#f59e0b' if i==src else '#dc2626' if i==dst else '#a855f7' if i in path and status=='route found' else '#16a34a' if i in {b for a,b in mprs} else '#2563eb')
        rad=14 if i in (src,dst) else 11
        canvas.create_oval(px-rad,py-rad,px+rad,py+rad,fill=color,outline='white',width=2)
        canvas.create_text(px+rad+3,py-rad-5,text=str(i),anchor='w',font=('Arial',12,'bold'))
        hitboxes.append((i,px,py))
    summary.config(text=f't = {t:.1f}s | nodes: {len(pos)} | physical links: {len(edges)} | MPR selections: {len(mprs)}')
    selected_id=selected.get()
    chosen=sorted(j for i,j in mprs if i==selected_id)
    selectors=sorted(i for i,j in mprs if j==selected_id)
    sent=[r for r in tx[(src,dst)] if r[0]<=t]
    received={seq for rt,seq in rx[(src,dst)] if rt<=t}
    ok=sum(seq in received for _,seq,_ in sent)
    accepted=sum(flag for _,_,flag in sent)
    lines=[f'시간: {t:.1f}초',f'출발: {src}    목적지: {dst}', '', 'OLSR 라우팅 테이블 기반 경로:', ' → '.join(map(str,path)),f'판정: {status}', '']
    if status=='route found':
        lines += [f'경유 링크 수: {len(path)-1}', '※ 실제 각 노드의 다음 홉 테이블을 이어 붙인 경로입니다.', '※ 단일 패킷의 실제 이동 기록은 아닙니다.', '']
    else: lines += ['※ 현재 기록된 라우팅 테이블로는 목적지까지의 경로를 완성할 수 없습니다.', '']
    lines += [f'UDP 시험 패킷 (누적, {src} → {dst}):',f'송신 시도: {len(sent)}',f'소켓 송신 성공: {accepted}',f'목적지 수신: {ok}',f'수신율: {100*ok/len(sent):.1f}%' if sent else '수신율: 아직 송신 없음','※ 각 노드 쌍은 약 5초부터 1초마다 송신합니다.', '※ 노드 쌍마다 최초 송신 시점은 조금씩 다릅니다.', '※ 모든 방향별 노드 쌍을 각각 시험한 결과입니다.', '※ 전체 노드 쌍의 동시 트래픽에 따른 간섭이 포함됩니다.', '']
    if selected_id in pos:
        lines += [f'클릭한 노드: {selected_id}',f'내가 선택한 MPR: {chosen}',f'나를 MPR로 선택한 노드: {selectors}']
    else: lines += ['노드를 클릭하면 MPR 선택 관계를 확인할 수 있습니다.']
    lines += ['', '색상: 주황=출발, 빨강=목적지,', '보라=경로 경유 노드, 초록 점선=MPR,', '빨간 화살표=라우팅 테이블 경로', '', '주의: 연한 연결선은 거리 기반입니다.', '실제 Wi-Fi 링크 성공을 뜻하지 않습니다.']
    detail.config(state='normal');detail.delete('1.0','end');detail.insert('1.0','\n'.join(lines));detail.config(state='disabled')

def click(event):
    for i,x,y in reversed(hitboxes):
        if (event.x-x)**2+(event.y-y)**2<=24**2:
            selected.set(i);return
    selected.set(-1)
canvas.bind('<Button-1>',click)
canvas.bind('<Configure>',draw)
for v in (index,source,dest,selected,show_physical,show_mpr):v.trace_add('write',draw)

def toggle():
    playing.set(not playing.get());play.config(text='⏸ Pause' if playing.get() else '▶ Play')
def reset():
    playing.set(False);play.config(text='▶ Play');index.set(0)
def tick():
    if playing.get():
        if index.get() < len(times)-1:
            index.set(index.get()+1)
        else:
            playing.set(False)
            play.config(text='▶ Play')
    # Original: 100 ms per frame at 1x; adjust the delay for playback speed.
    root.after(max(10, round(100 / speed.get())), tick)

play=tk.Button(bar,text='▶ Play',command=toggle);play.pack(side='left')
tk.Button(bar,text='↺ Reset',command=reset).pack(side='left',padx=4)
tk.Label(bar,text='출발',bg='#edf2f7').pack(side='left',padx=(12,2))
def upward_node_menu(parent, variable):
    """Show node choices above the bottom toolbar instead of below it."""
    button = tk.Menubutton(parent, textvariable=variable, relief='raised',
                           borderwidth=2, indicatoron=True, width=4)
    menu = tk.Menu(button, tearoff=False)
    for node in node_ids:
        menu.add_radiobutton(label=str(node), value=node, variable=variable)
    button.configure(menu=menu, direction='above')
    button.pack(side='left')
    return button

upward_node_menu(bar, source)
tk.Label(bar,text='목적지',bg='#edf2f7').pack(side='left',padx=(12,2))
upward_node_menu(bar, dest)
tk.Checkbutton(bar,text='전체 링크',variable=show_physical,bg='#edf2f7').pack(side='left',padx=8)
tk.Checkbutton(bar,text='MPR',variable=show_mpr,bg='#edf2f7').pack(side='left',padx=8)
tk.Label(bar,text='재생 속도',bg='#edf2f7').pack(side='left',padx=(8,2))
speed_label = tk.Label(bar,text='1.0×',bg='#edf2f7',width=5)
def update_speed(value):
    speed.set(float(value))
    speed_label.config(text=f'{speed.get():.2g}×')
speed_slider = tk.Scale(bar,from_=0.25,to=4.0,resolution=0.25,
                        orient='horizontal',showvalue=False,length=145,
                        bg='#edf2f7',highlightthickness=0,command=update_speed)
speed_slider.set(1.0)
speed_slider.pack(side='left',padx=(0,2))
speed_label.pack(side='left')
tk.Scale(bar,from_=0,to=len(times)-1,orient='horizontal',variable=index,showvalue=False,bg='#edf2f7',highlightthickness=0).pack(side='left',fill='x',expand=True,padx=10)
root.after(100,draw);tick();root.mainloop()
