import time
import random
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import sys
import os

# Try importing platform-specific non-blocking input modules
try:
    import select
    import termios, tty
    def kbhit_nonblocking():
        """Check if a key is pressed (Unix-like). Returns True if input is ready."""
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        return dr != []
    def get_char_nonblocking():
        """Read a character non-blockingly (Unix-like)."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            ch = sys.stdin.read(1)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
except ImportError:
    try:
        import msvcrt
        def kbhit_nonblocking():
            """Check if a key is pressed (Windows). Returns True if input is ready."""
            return msvcrt.kbhit()
        def get_char_nonblocking():
            """Read a character non-blockingly (Windows)."""
            return msvcrt.getch().decode('utf-8')
    except ImportError:
        def kbhit_nonblocking():
            return False
        def get_char_nonblocking():
            return None
        print("警告：無法啟用非阻塞輸入。菜單中斷功能可能無法正常運作。")


console = Console()

# --- 全域變數初始化 ---
ore_count = 0
ore_per_mine = 1
multiplier = 1.0
history = []
mine_interval = 2  # 自動挖礦間隔 (秒)
event_interval_min = 5  # 隨機事件最小間隔 (秒)
event_interval_max = 10 # 隨機事件最大間隔 (秒)
event_chance = 0.5 # 事件觸發機率 (50%)

last_mine_time = time.time()
initial_event_trigger_time = time.time() + 5 # 第一次事件的目標時間
next_event_time = initial_event_trigger_time # 下一次事件檢查時間
game_running = True
first_event_triggered = False # 追蹤第一次事件是否已觸發
game_ended_by_event = False # 追蹤遊戲是否因結局事件結束
current_event = None # 追蹤當前事件狀態
current_message = "" # 儲存需要即時顯示的訊息

# 初期山洞事件池
initial_events = [
    {
        "desc": "角落有一本發霉的筆記本，寫著『別再往下挖了』。",
        "choices": ["翻閱內容", "焚燒詛咒"],
        "outcomes": ["你覺得有點不安，但什麼事也沒發生。",
                     "詛咒似乎隨煙霧散去，你感覺輕鬆些。"]
    },
    {
        "desc": "你踩到一塊鬆動的岩石，地板出現一個小洞。你決定...",
        "choices": ["跳下去看看", "用石頭填起來"],
        "outcomes": ["你發現了額外礦脈，獲得 +3 礦石！", "安全為上，繼續挖礦。"],
        "reward": 3
    },
    {
        "desc": "你看到一具舊礦工的遺骸，旁邊有閃亮的東西。",
        "choices": ["撿起來", "默哀離開"],
        "outcomes": ["你獲得一把古老的鐵鎬！產出翻倍！", "你低頭致意，什麼也沒拿。"],
        "upgrade": True
    },
    {
        "desc": "你發現一堵牆上刻著奇怪的符號。",
        "choices": ["嘗試解讀", "無視走過"],
        "outcomes": ["你感覺到腦中湧入知識的片段，智慧提升！", "你錯過了某種機會。"],
        "upgrade": True
    },
    {
        "desc": "前方是兩條分岔路。",
        "choices": ["走左邊的潮濕通道", "走右邊的乾燥通道"],
        "outcomes": ["你被滑倒，損失了些體力。", "你撿到一枚閃亮的金幣！"],
        "reward": 1
    },
    {
        "desc": "你聽見低語聲從牆後傳來。",
        "choices": ["靠近傾聽", "拔腿就跑"],
        "outcomes": ["聲音消失了，你感覺一陣寒意。", "你撞到一根 stalagmite，額頭腫了一塊。"]
    },
    {
        "desc": "地上有個破舊背包。",
        "choices": ["翻找看看", "小心繞過"],
        "outcomes": ["你找到一瓶恢復藥水。", "你錯過了可能的物資。"],
        "reward": 1
    },
    {
        "desc": "你發現一根微微發光的礦脈。",
        "choices": ["挖掘它", "先標記位置再走"],
        "outcomes": ["你獲得 +5 魔礦，但體力大減。", "你安全離開，稍後再來。"],
        "reward": 5
    },
    {
        "desc": "某種氣體從縫隙冒出。",
        "choices": ["深呼吸觀察效果", "摀住口鼻快逃"],
        "outcomes": ["你感覺頭暈，好像看見幻覺。", "你安全撤離，沒受傷。"],
    },
    {
        "desc": "你發現牆上插著一把生鏽的劍。",
        "choices": ["拔出來", "不動它"],
        "outcomes": ["劍斷了，你受了點傷。", "你感到一股壓抑的力量繼續潛伏。"]
    },
    {
        "desc": "天花板開始掉落碎石。",
        "choices": ["就地閃避", "高舉背包擋住"],
        "outcomes": ["你成功閃過！", "背包破了，物資掉了一些。"],
    },
    {
        "desc": "一隻蝙蝠從陰影中衝出。",
        "choices": ["揮動工具驅趕", "縮身不動"],
        "outcomes": ["你嚇走牠並發現牠藏匿的小寶石！", "牠撞到你，造成一點損傷。"],
        "reward": 1
    },
    {
        "desc": "你踩到一個舊陷阱機關。",
        "choices": ["拆解它", "小心繞過"],
        "outcomes": ["你拆除陷阱並獲得機械零件！", "你安全通過。"],
        "reward": 2
    },
    {
        "desc": "你發現一小塊骨頭拼圖。",
        "choices": ["組合看看", "直接丟棄"],
        "outcomes": ["一塊秘密門打開了！你進入隱藏房間！", "你錯過了秘密通道。"],
        "upgrade": True
    },
    {
        "desc": "一隻蛇突然竄出。",
        "choices": ["揮舞工具嚇走牠", "靜止不動等待"],
        "outcomes": ["你被咬了一口，有點中毒。", "牠滑走了，你鬆一口氣。"],
    },
    {
        "desc": "牆縫中隱約傳來哼唱聲。",
        "choices": ["跟著哼唱", "裝作沒聽到"],
        "outcomes": ["你的心情奇妙地平靜下來。", "你總覺得有什麼錯過了。"]
    },
    {
        "desc": "你發現一塊畫有笑臉的石頭。",
        "choices": ["收進背包", "踢開它"],
        "outcomes": ["你獲得幸運加成！", "你腳痛了一整天。"],
        "upgrade": True
    },
    {
        "desc": "洞內牆面濕滑，上面長滿了不明苔蘚。",
        "choices": ["採集樣本", "避開前進"],
        "outcomes": ["你獲得神秘藥材，可能有用！", "你避免中毒風險。"],
        "reward": 1
    },
    {
        "desc": "你碰到一根半截木柱。",
        "choices": ["拔起來", "當作路標"],
        "outcomes": ["底下藏著一袋古幣！", "你繼續向前。"],
        "reward": 2
    },
    {
        "desc": "你聽見迴響的笑聲從深處傳來。",
        "choices": ["往聲音處走", "遠離那區"],
        "outcomes": ["你發現一具倒下的假人，驚嚇一場。", "你錯過一個彩蛋房間。"]
    },
    {
        "desc": "地上散落一些破布與鐵片。",
        "choices": ["拼成什麼裝備", "不理會"],
        "outcomes": ["你成功組成一件破爛護肩，略微防禦上升。", "你選擇保持輕裝前進。"],
        "upgrade": True
    },
    {
        "desc": "地面有明顯被挖掘過的痕跡。",
        "choices": ["挖掘看看", "繞開不碰"],
        "outcomes": ["你發現一顆古代寶石！", "你選擇不貪心。"],
        "reward": 4
    },
    {
        "desc": "你腳邊有一隻縮成一團的小動物。",
        "choices": ["輕聲安撫", "把牠趕開"],
        "outcomes": ["牠咬你一口逃走，你有些受傷。", "牠驚慌逃離。"]
    },
    {
        "desc": "你看到前方有微弱的藍光。",
        "choices": ["走近看看", "關掉燈前進"],
        "outcomes": ["你找到一個古老水晶，似乎有魔力。", "你摸黑前進但沒撞到東西。"],
        "reward": 1,
        "upgrade": True
    },
    {
        "desc": "你踩到某種軟綿綿的東西。",
        "choices": ["低頭觀察", "趕快移開腳"],
        "outcomes": ["是稀有的螢光苔蘚，可用來煉金！", "你逃開但鞋子濕了。"],
        "reward": 2
    },
    {
        "desc": "你發現一根不斷滴水的 stalactite。",
        "choices": ["接水喝喝看", "避免接觸"],
        "outcomes": ["你恢復了一些體力！", "你錯過了一次回復機會。"],
        "upgrade": True
    },
    {
        "desc": "地板忽然凹陷陷落！",
        "choices": ["跳開", "試圖抓住旁邊的岩壁"],
        "outcomes": ["你安全跳過去了！", "你滑下洞穴，受了一點傷。"],
    },
    {
        "desc": "你看到牆上貼著一張泛黃海報。",
        "choices": ["撕下來研究", "保留原地"],
        "outcomes": ["你獲得一段失落礦工的記錄。", "你尊重歷史，靜靜走開。"]
    },
    {
        "desc": "遠處有機械聲與微光。",
        "choices": ["靠近看看", "立刻撤退"],
        "outcomes": ["你發現一台還能運作的挖礦裝置！", "你錯過一次工具升級機會。"],
        "upgrade": True
    },
    {
        "desc": "牆上有一個骷髏頭被紅繩綁住。",
        "choices": ["觸碰它", "背對快走"],
        "outcomes": ["你感到一股邪氣纏上你。", "你避開了未知的詛咒。"],
    },
    {
        "desc": "你摸到一塊發熱的石頭。",
        "choices": ["收起來", "丟掉它"],
        "outcomes": ["你獲得火焰礦石，可用來鍛造！", "你錯失了罕見資源。"],
        "reward": 3
    },
    {
        "desc": "你發現一把插在地上的鏽釘木牌。",
        "choices": ["閱讀內容", "把它拆下"],
        "outcomes": ["上面寫著：『這裡不歡迎外人』，你感覺不寒而慄。", "你把它拆下，什麼也沒發生。"]
    }

]



# 最終章事件池 (已簡化)
final_chapter_events = [
    {
        "type": "normal",
        "desc": "你挖到了地下深處，發現一個廣闊的地下湖泊。",
        "choices": ["飲用湖水", "繞道而行"],
        "outcomes": ["你感覺精神飽滿，單次產出提升 5！", "你安全通過，無事發生。"],
        "ore_per_mine_boost": {"idx": 0, "value": 5} # 簡化為直接提升單次產出
    },
    {
        "type": "normal",
        "desc": "牆壁上刻著古老的符文，散發著微光。",
        "choices": ["觸摸符文", "拍照紀錄"],
        "outcomes": ["你獲得古老智慧的啟迪，倍率提升 0.2x！", "你無實際影響，只留下紀念。"],
        "multiplier_boost": {"idx": 0, "value": 0.2} # 簡化為直接提升倍率
    },
    {
        "type": "normal",
        "desc": "一種奇特的發光生物從陰影中竄出。",
        "choices": ["嘗試捕捉", "靜觀其變"],
        "outcomes": ["你獲得了額外礦石！", "生物自行離去，無事發生。"],
        "reward": 10 # 簡化為直接獲得礦石
    },
    {
        "type": "normal",
        "desc": "聽到遠處傳來隆隆聲，似乎有小規模塌方。",
        "choices": ["加固周圍", "快速挖礦"],
        "outcomes": ["你花費少量礦石加固了周圍，感覺更安全。", "你選擇了快速挖礦，無事發生。"],
        "ore_cost": {"idx": 0, "cost": 3} # 簡化為少量礦石花費，沒有後續風險
    },
    {
        "type": "ending",
        "desc": "你持續挖礦，工具不斷深入，突然，前方一片光明，你感覺到巨大的空間！你挖通了整個礦脈，抵達了另一端，看到了從未見過的景象。這趟挖礦旅程，終於抵達了終點！",
        "choices": ["離開礦洞", "再次深入 (無效)"], # 實際上只有一個選項能結束遊戲
        "outcomes": ["你成功地挖通了礦脈，完成了這趟旅程！", "你試圖再次深入，但礦洞已經走到盡頭。"]
    }
]

current_active_events = initial_events # 遊戲開始時使用初期事件池

# 由於簡化事件，不再需要臨時效果列表
# temp_effects = [] 

# 移除不再需要的臨時效果函數
# def apply_temp_effect(stat, value, duration):
#     global ore_per_mine, multiplier
#     end_time = time.time() + duration
#     temp_effects.append({"stat": stat, "value": value, "end_time": end_time})
#     if stat == "ore_per_mine":
#         ore_per_mine += value
#     elif stat == "multiplier":
#         multiplier += value # 臨時倍率加成

# def remove_expired_temp_effects():
#     global ore_per_mine, multiplier
#     expired = []
#     for effect in temp_effects:
#         if time.time() >= effect["end_time"]:
#             expired.append(effect)
#             if effect["stat"] == "ore_per_mine":
#                 ore_per_mine -= effect["value"]
#             elif effect["stat"] == "multiplier":
#                 multiplier -= effect["value"]
#     for effect in expired:
#         temp_effects.remove(effect)
#         log(f"[dim]臨時效果已結束：{effect['stat']} {effect['value']}[/dim]")


def log(msg, immediate_display=False, event_log=False):
    """將訊息加入歷史記錄。如果 immediate_display 為 True，則設置為當前訊息。
       event_log=True 表示這是一個山洞事件的記錄，用於最終篩選。"""
    global current_message
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    entry = f"{timestamp} {msg}"
    
    # 儲存完整的記錄，以及一個標記判斷是否為事件相關
    history.append({"text": entry, "is_event": event_log})
    
    if immediate_display:
        current_message = msg # 設定為最新需要即時顯示的訊息

def render_status():
    """返回當前遊戲狀態的 Rich Panel 物件"""
    panel = Panel.fit(f"礦石：[yellow]{ore_count}[/yellow] 顆\n"
                      f"單次產出：[green]{ore_per_mine}[/green]\n"
                      f"倍率：[cyan]{multiplier}x[/cyan]", title="⛏️ [bold blue]狀態[/bold blue]")
    return panel

def render_history_snippet():
    """返回歷史記錄的 Rich Table 物件 (顯示最近幾條記錄)"""
    table = Table(title="📜 [bold magenta]遊戲紀錄 (近期歷史)[/bold magenta]")
    table.add_column("時間", style="dim", width=12)
    table.add_column("紀錄", style="white")
    # 顯示最新的 5 條記錄
    # 這裡的 history 項目現在是字典，需要取 'text'
    for entry_dict in history[-5:]:
        entry = entry_dict['text']
        if entry.startswith("["):
            time_part, msg_part = entry.split("] ", 1)
            table.add_row(time_part + "]", msg_part)
        else:
            table.add_row("", entry)
    if not table.rows:
        table.add_row("", "[dim]沒有更多近期歷史記錄。[/dim]")
    return table

def render_event_history():
    """返回所有山洞事件的 Rich Table 物件 (用於遊戲結束)"""
    table = Table(title="📜 [bold magenta]山洞事件記錄[/bold magenta]")
    table.add_column("時間", style="dim", width=12)
    table.add_column("事件記錄", style="white")
    
    event_records = [item for item in history if item["is_event"]]
    
    if not event_records:
        table.add_row("", "[dim]沒有山洞事件記錄。[/dim]")
    for entry_dict in event_records:
        entry = entry_dict['text']
        if entry.startswith("["):
            time_part, msg_part = entry.split("] ", 1)
            table.add_row(time_part + "]", msg_part)
        else:
            table.add_row("", entry)
    return table

def trigger_random_event():
    """觸發一個隨機事件"""
    global current_event, current_active_events
    
    # 如果達到單次產出 50，切換到最終章事件池
    if ore_per_mine >= 50 and current_active_events is not final_chapter_events:
        current_active_events = final_chapter_events
        log("[bold yellow]你感覺礦洞深處傳來異樣的氣息，似乎有新的事件正在靠近...[/bold yellow]", immediate_display=True, event_log=True) # 切換事件池也作為事件記錄
        time.sleep(1) # 給點時間讓玩家看到訊息
        
    event = random.choice(current_active_events)
    current_event = event
    log(f"[bold red]事件觸發！[/bold red]", immediate_display=True, event_log=True) # 標記為事件記錄

def mine_once():
    """執行一次挖礦操作"""
    global ore_count
    gain = int(ore_per_mine * multiplier)
    ore_count += gain
    log(f"你挖到 [yellow]{gain}[/yellow] 顆礦石。總共：[yellow]{ore_count}[/yellow]") # 普通挖礦不標記 event_log

def process_event_choice(raw_choice_num):
    """處理事件選擇並應用結果"""
    global ore_count, ore_per_mine, multiplier, current_event, game_running, game_ended_by_event
    
    if current_event:
        # 事件選項從 5/6，對應到 choices 列表的索引 0/1
        actual_choice_idx = raw_choice_num - 5 
        
        if 0 <= actual_choice_idx < len(current_event["choices"]):
            log(f"你選擇了：[bold green]{current_event['choices'][actual_choice_idx]}[/bold green]", immediate_display=True, event_log=True)
            outcome_msg = current_event["outcomes"][actual_choice_idx]
            log(outcome_msg, immediate_display=True, event_log=True)

            # 處理結局事件
            if current_event.get("type") == "ending" and actual_choice_idx == 0:
                game_ended_by_event = True
                game_running = False # 設置為 False 結束主循環
                log("[bold green]你已挖通礦脈，遊戲結束！[/bold green]", immediate_display=True, event_log=True)
                return # 直接返回，結束事件處理，準備結束遊戲

            # --- 處理簡化後的事件效果 ---
            if "reward" in current_event and actual_choice_idx == 0: # 假設獎勵總是選項0
                ore_count += current_event["reward"]
                log(f"額外獲得 [yellow]{current_event['reward']}[/yellow] 礦石！", immediate_display=True, event_log=True)
            
            if "upgrade" in current_event and actual_choice_idx == 0: # 假設升級總是選項0
                multiplier *= 2
                ore_per_mine = int(ore_per_mine * 2)
                log("[bold yellow]你的工具升級了！產出翻倍！[/bold yellow]", immediate_display=True, event_log=True)
            
            # 新增簡化後的最終章事件效果處理
            if "ore_per_mine_boost" in current_event and actual_choice_idx == current_event["ore_per_mine_boost"]["idx"]:
                ore_per_mine += current_event["ore_per_mine_boost"]["value"]
                log(f"單次產出提升 [green]{current_event['ore_per_mine_boost']['value']}[/green]！", immediate_display=True, event_log=True)

            if "multiplier_boost" in current_event and actual_choice_idx == current_event["multiplier_boost"]["idx"]:
                multiplier += current_event["multiplier_boost"]["value"]
                log(f"倍率提升 [cyan]{current_event['multiplier_boost']['value']:.1f}x[/cyan]！", immediate_display=True, event_log=True)
            
            if "ore_cost" in current_event and actual_choice_idx == current_event["ore_cost"]["idx"]:
                cost = current_event["ore_cost"]["cost"]
                if ore_count >= cost:
                    ore_count -= cost
                    log(f"你花費 [yellow]{cost}[/yellow] 礦石加固了周圍。", immediate_display=True, event_log=True)
                else:
                    log("[red]礦石不足，無法執行此操作。[/red]", immediate_display=True, event_log=True)


            current_event = None # 事件處理完畢
        else:
            log("[red]無效的事件選擇。[/red]", immediate_display=True, event_log=True)
    else:
        log("[dim]目前沒有活躍事件可供選擇。[/dim]", immediate_display=True)

def display_game_state():
    """清除屏幕並顯示當前遊戲狀態、即時訊息和菜單"""
    console.clear()
    console.print(render_status())

    # 即時顯示最新的行動訊息
    if current_message:
        console.print(Panel(Text(current_message, justify="center"), title="💡 [bold yellow]最新動態[/bold yellow]", expand=False))
    else:
        # 確保這裡顯示的是正確的標題
        console.print(Panel(Text("等待中...", justify="center", style="dim"), title="💡 [bold yellow]最新動態[/bold yellow]", expand=False))

    # 顯示近期歷史記錄片段
    console.print(render_history_snippet())

    if current_event:
        event_panel = Panel(current_event["desc"], title="🌑 [bold white]山洞事件[/bold white]", expand=False)
        console.print(event_panel)
        # 事件選項現在顯示為 5 和 6
        console.print(f"[bold]5[/bold]. [cyan]{current_event['choices'][0]}[/cyan]")
        console.print(f"[bold]6[/bold]. [cyan]{current_event['choices'][1]}[/cyan]")
        console.print("\n[italic dim]請輸入你的選擇 (5/6):[/italic dim]")
    else:
        menu_panel = Panel(
            "1. 升級工具 ([yellow]10礦[/yellow])\n"
            "2. 查看狀態\n"
            "3. 離開遊戲\n"
            "4. 查看紀錄",
            title="⚙️ [bold green]菜單[/bold green]",
            expand=False
        )
        console.print(menu_panel)
        console.print("[italic dim]遊戲自動進行中。按 [bold yellow]Enter[/bold yellow] 鍵打開菜單...[/italic dim]")

def handle_menu_choice():
    """處理菜單選項的邏輯 (會阻塞等待輸入)"""
    global game_running, ore_count, ore_per_mine, multiplier, current_message
    console.print("\n[bold green]-- 菜單模式 --[/bold green]")
    try:
        choice = console.input("[yellow]請輸入菜單選項 [1/2/3/4]: [/yellow]").strip()
        if choice == "1":
            if ore_count >= 10:
                ore_count -= 10
                ore_per_mine += 1
                log("你升級了工具！單次產出提升。", immediate_display=True)
            else:
                log("[red]礦石不足，無法升級。[/red]", immediate_display=True)
        elif choice == "2":
            log("[dim]狀態已刷新。[/dim]", immediate_display=True)
        elif choice == "3":
            log("你離開了礦井。遊戲結束。", immediate_display=True)
            game_running = False
        elif choice == "4":
            console.clear()
            # 在菜單中查看記錄時，顯示所有記錄 (不只事件)
            table = Table(title="📜 [bold magenta]完整遊戲紀錄[/bold magenta]")
            table.add_column("時間", style="dim", width=12)
            table.add_column("紀錄", style="white")
            if not history:
                table.add_row("", "[dim]目前沒有任何記錄。[/dim]")
            for entry_dict in history:
                entry = entry_dict['text']
                if entry.startswith("["):
                    time_part, msg_part = entry.split("] ", 1)
                    table.add_row(time_part + "]", msg_part)
                else:
                    table.add_row("", entry)
            console.print(table)
            console.input("[yellow]按下 Enter 鍵返回遊戲...[/yellow]")
            current_message = "" # 返回後清空最新訊息
        elif choice:
            log(f"[red]無效選項: {choice}[/red]", immediate_display=True)
        else: # 如果用戶直接按 Enter
            log("[dim]已返回遊戲自動進程。[/dim]", immediate_display=True)

    except EOFError:
        log("[red]遊戲被中斷。[/red]", immediate_display=True)
        game_running = False
    except Exception as e:
        log(f"[red]菜單輸入錯誤: {e}[/red]", immediate_display=True)
    finally:
        pass

# 遊戲開始畫面
console.clear()
console.print(Panel("🪨 [bold green]歡迎來到《Codexu3 礦井》！[/bold green]\n"
                    "遊戲將自動進行挖礦與事件探索。\n"
                    "事件發生時請做出選擇，按 [bold yellow]Ctrl+C[/bold yellow] 退出遊戲。\n"
                    "在非事件期間，按 [bold yellow]Enter[/bold yellow] 鍵可開啟菜單。", title="👷‍♂️ [bold yellow]掛機文字冒險[/bold yellow]"))
time.sleep(3) # 讓玩家看清楚開場白

# 主循環
while game_running:
    now = time.time()
    # 由於簡化事件，不再需要移除臨時效果
    # remove_expired_temp_effects() 

    # 自動挖礦
    if now - last_mine_time >= mine_interval:
        mine_once()
        last_mine_time = now

    # 事件觸發點
    if now >= next_event_time and current_event is None:
        if not first_event_triggered:
            log("[bold red]第一次事件即將觸發！[/bold red]", immediate_display=True)
            trigger_random_event() # 第一次直接觸發，不受機率限制
            first_event_triggered = True
        elif random.random() < event_chance: # 後續事件則根據機率觸發
            trigger_random_event()
        else:
            log("[dim]沒有事件發生，繼續挖礦...[/dim]", immediate_display=True)
            
        # 無論是否觸發事件，都重新設定下一次事件檢查時間
        next_event_time = now + random.randint(event_interval_min, event_interval_max)
        
    display_game_state() # 每次循環都刷新屏幕

    # 檢查是否有事件需要處理
    if current_event:
        # 事件發生，阻塞式等待輸入
        while True:
            try:
                # 提示輸入 5 或 6
                choice = console.input("[yellow]你的選擇[/yellow] [5/6]: ").strip()
                if choice in ["5", "6"]:
                    process_event_choice(int(choice))
                    # 在 process_event_choice 中處理了 game_running 的結束，
                    # 所以這裡只需要檢查是否結束，如果結束就跳出所有循環
                    if not game_running:
                        break # 跳出事件輸入循環
                    current_message = "" # 清空最新訊息
                    break
                else:
                    console.print("[red]無效輸入，請輸入 5 或 6。[/red]")
            except EOFError:
                console.print("[red]遊戲被中斷。[/red]")
                game_running = False
                break
            except Exception as e:
                console.print(f"[red]輸入錯誤: {e}[/red]")
                continue
    else:
        # 非事件期間：檢查是否有來自用戶的菜單輸入請求 (非阻塞)
        if kbhit_nonblocking(): # 檢查是否有按鍵被按下
            ch = get_char_nonblocking()
            if ch == '\n' or ch == '\r': # 偵測到 Enter 鍵 (Unix-like: '\n', Windows: '\r\n' -> '\r')
                # 清空 stdin 緩衝區，防止多餘的字符影響後續輸入
                if sys.stdin.isatty(): # 確保在交互式終端才這麼做
                    try:
                        while kbhit_nonblocking(): # 讀取所有剩餘的字符直到緩衝區清空
                            get_char_nonblocking()
                    except Exception:
                        pass # 避免在某些終端出錯

                handle_menu_choice() # 進入菜單處理模式 (此時會阻塞)
            
    # 檢查遊戲是否因結局事件結束 (放在這裡確保顯示完最後一次狀態才結束)
    if game_ended_by_event:
        break # 跳出主循環

    time.sleep(0.1) # 短暫延遲，讓畫面變化可見，避免 CPU 爆轉

# 遊戲結束後顯示最終狀態和完整歷史記錄
console.clear()
# 如果遊戲是因結局事件結束，則 log 訊息已經在 process_event_choice 中處理
if not game_ended_by_event:
    log("你離開了礦井。遊戲結束。", immediate_display=True)

console.print(f"\n你的最終單次產出：[green]{ore_per_mine}[/green]")
console.print(render_event_history()) # 顯示所有山洞事件記錄
console.print("[bold red]感謝遊玩！[/bold red]")