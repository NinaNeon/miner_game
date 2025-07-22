// --- DOM 元素引用 ---
const oreCountElem = document.getElementById('ore-count');
const orePerMineElem = document.getElementById('ore-per-mine');
const multiplierElem = document.getElementById('multiplier');
const currentMessageElem = document.getElementById('current-message');
const historyLogElem = document.getElementById('history-log');

const eventPanel = document.getElementById('event-panel');
const eventDescriptionElem = document.getElementById('event-description');
const choice5Btn = document.getElementById('choice-5-btn');
const choice6Btn = document.getElementById('choice-6-btn');

const menuPanel = document.getElementById('menu-panel');
const menuUpgradeBtn = document.getElementById('menu-upgrade');
const menuStatusBtn = document.getElementById('menu-status');
const menuExitBtn = document.getElementById('menu-exit');
const menuViewLogBtn = document.getElementById('menu-view-log');

const overlay = document.getElementById('overlay');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const modalCloseBtn = document.getElementById('modal-close-btn');

// --- 遊戲狀態變數 ---
let oreCount = 0;
let orePerMine = 1;
let multiplier = 1.0;
let history = []; // [{text: "...", is_event: true/false}]
let mineInterval = 2; // 自動挖礦間隔 (秒)
let eventIntervalMin = 5; // 隨機事件最小間隔 (秒)
let eventIntervalMax = 10; // 隨機事件最大間隔 (秒)
let eventChance = 0.5; // 事件觸發機率 (50%)

let lastMineTime = Date.now(); // 使用 Date.now() 獲取毫秒時間戳
let initialEventTriggerTime = Date.now() + 5 * 1000; // 第一次事件的目標時間
let nextEventTime = initialEventTriggerTime; // 下一次事件檢查時間
let gameRunning = true;
let firstEventTriggered = false;
let gameEndedByEvent = false;
let currentEvent = null; // 追蹤當前事件狀態

// --- 事件定義 ---
const initialEvents = [
    {
        "type": "normal",
        "desc": "角落有一本發霉的筆記本，寫著『別再往下挖了』。",
        "choices": ["翻閱內容", "焚燒詛咒"],
        "outcomes": ["你覺得有點不安，但什麼事也沒發生。",
                     "詛咒似乎隨煙霧散去，你感覺輕鬆些。"]
    },
    {
        "type": "normal",
        "desc": "你踩到一塊鬆動的岩石，地板出現一個小洞。你決定...",
        "choices": ["跳下去看看", "用石頭填起來"],
        "outcomes": ["你發現了額外礦脈，獲得 +3 礦石！", "安全為上，繼續挖礦。"],
        "reward": 3
    },
    {
        "type": "normal",
        "desc": "你看到一具舊礦工的遺骸，旁邊有閃亮的東西。",
        "choices": ["撿起來", "默哀離開"],
        "outcomes": ["你獲得一把古老的鐵鎬！產出翻倍！", "你低頭致意，什麼也沒拿。"],
        "upgrade": true
    }
];

const finalChapterEvents = [
    {
        "type": "normal",
        "desc": "你挖到了地下深處，發現一個廣闊的地下湖泊。",
        "choices": ["飲用湖水", "繞道而行"],
        "outcomes": ["你感覺精神飽滿，單次產出提升 5！", "你安全通過，無事發生。"],
        "ore_per_mine_boost": {"idx": 0, "value": 5}
    },
    {
        "type": "normal",
        "desc": "牆壁上刻著古老的符文，散發著微光。",
        "choices": ["觸摸符文", "拍照紀錄"],
        "outcomes": ["你獲得古老智慧的啟迪，倍率提升 0.2x！", "你無實際影響，只留下紀念。"],
        "multiplier_boost": {"idx": 0, "value": 0.2}
    },
    {
        "type": "normal",
        "desc": "一種奇特的發光生物從陰影中竄出。",
        "choices": ["嘗試捕捉", "靜觀其變"],
        "outcomes": ["你獲得了額外礦石！", "生物自行離去，無事發生。"],
        "reward": 10
    },
    {
        "type": "normal",
        "desc": "聽到遠處傳來隆隆聲，似乎有小規模塌方。",
        "choices": ["加固周圍", "快速挖礦"],
        "outcomes": ["你花費少量礦石加固了周圍，感覺更安全。", "你選擇了快速挖礦，無事發生。"],
        "ore_cost": {"idx": 0, "cost": 3}
    },
    {
        "type": "ending",
        "desc": "你持續挖礦，工具不斷深入，突然，前方一片光明，你感覺到巨大的空間！你挖通了整個礦脈，抵達了另一端，看到了從未見過的景象。這趟挖礦旅程，終於抵達了終點！",
        "choices": ["離開礦洞", "再次深入 (無效)"],
        "outcomes": ["你成功地挖通了礦脈，完成了這趟旅程！", "你試圖再次深入，但礦洞已經走到盡頭。"]
    }
];

let currentActiveEvents = initialEvents;

// --- 輔助函數 ---
function formatRichText(text) {
    // 簡單地轉換 Rich 庫的顏色標籤到 CSS 類名
    let formattedText = text;
    formattedText = formattedText.replace(/\[yellow\](.*?)\[\/yellow\]/g, '<span class="yellow-text">$1</span>');
    formattedText = formattedText.replace(/\[green\](.*?)\[\/green\]/g, '<span class="green-text">$1</span>');
    formattedText = formattedText.replace(/\[cyan\](.*?)\[\/cyan\]/g, '<span class="cyan-text">$1</span>');
    formattedText = formattedText.replace(/\[bold\](.*?)\[\/bold\]/g, '<span class="bold-text">$1</span>');
    formattedText = formattedText.replace(/\[red\](.*?)\[\/red\]/g, '<span class="red-text">$1</span>');
    formattedText = formattedText.replace(/\[magenta\](.*?)\[\/magenta\]/g, '<span class="magenta-text">$1</span>');
    formattedText = formattedText.replace(/\[blue\](.*?)\[\/blue\]/g, '<span class="blue-text">$1</span>');
    formattedText = formattedText.replace(/\[dim\](.*?)\[\/dim\]/g, '<span class="dim-text">$1</span>');
    formattedText = formattedText.replace(/\[italic dim\](.*?)\[\/italic dim\]/g, '<span class="dim-text italic-text">$1</span>'); // Assuming italic-text is defined in CSS
    formattedText = formattedText.replace(/\[bold yellow\](.*?)\[\/bold yellow\]/g, '<span class="bold-text yellow-text">$1</span>');
    formattedText = formattedText.replace(/\[bold green\](.*?)\[\/bold green\]/g, '<span class="bold-text green-text">$1</span>');
    formattedText = formattedText.replace(/\[bold red\](.*?)\[\/bold red\]/g, '<span class="bold-text red-text">$1</span>');
    formattedText = formattedText.replace(/\[bold white\](.*?)\[\/bold white\]/g, '<span class="bold-text white-text">$1</span>');


    // 移除所有未被替換的 Rich 標籤
    formattedText = formattedText.replace(/\[.*?\]/g, '');

    return formattedText;
}

function log(msg, immediateDisplay = false, eventLog = false) {
    const timestamp = new Date().toLocaleTimeString('zh-TW', { hour12: false });
    const entry = `[${timestamp}] ${msg}`;
    history.push({ text: entry, is_event: eventLog });

    if (immediateDisplay) {
        currentMessageElem.innerHTML = formatRichText(msg);
    }

    // 更新近期歷史記錄顯示
    updateHistorySnippet();
}

function updateStatusDisplay() {
    oreCountElem.textContent = oreCount;
    orePerMineElem.textContent = orePerMine;
    multiplierElem.textContent = multiplier.toFixed(1); // 倍率保留一位小數
}

function updateHistorySnippet() {
    historyLogElem.innerHTML = ''; // 清空現有內容
    const recentHistory = history.slice(-5); // 獲取最新的 5 條記錄

    if (recentHistory.length === 0) {
        historyLogElem.innerHTML = '<p class="dim-text">沒有更多近期歷史記錄。</p>';
        return;
    }

    recentHistory.forEach(entry => {
        const p = document.createElement('p');
        // 對時間戳進行特殊處理，使其顏色不會被覆蓋
        const timePartMatch = entry.text.match(/^\[(.*?)\]\s*(.*)/);
        if (timePartMatch) {
            p.innerHTML = `<span class="dim-text">[${timePartMatch[1]}]</span> ${formatRichText(timePartMatch[2])}`;
        } else {
            p.innerHTML = formatRichText(entry.text);
        }
        historyLogElem.appendChild(p);
    });
    // 讓滾動條保持在底部
    historyLogElem.scrollTop = historyLogElem.scrollHeight;
}

function showModal(title, contentHtml) {
    modalTitle.textContent = title;
    modalBody.innerHTML = contentHtml;
    overlay.classList.remove('hidden');
}

function closeModal() {
    overlay.classList.add('hidden');
}

// --- 遊戲邏輯函數 ---
function triggerRandomEvent() {
    // 如果達到單次產出 50，切換到最終章事件池
    if (orePerMine >= 50 && currentActiveEvents !== finalChapterEvents) {
        currentActiveEvents = finalChapterEvents;
        log("[bold yellow]你感覺礦洞深處傳來異樣的氣息，似乎有新的事件正在靠近...[/bold yellow]", true, true);
        setTimeout(() => { // 短暫延遲後再顯示事件，讓訊息能被看見
            const event = getRandomEvent();
            displayEvent(event);
        }, 1000);
        return;
    }
    
    const event = getRandomEvent();
    displayEvent(event);
}

function getRandomEvent() {
    return currentActiveEvents[Math.floor(Math.random() * currentActiveEvents.length)];
}

function displayEvent(event) {
    currentEvent = event;
    log(`[bold red]事件觸發！[/bold red]`, true, true);
    eventDescriptionElem.innerHTML = formatRichText(event.desc);
    choice5Btn.innerHTML = formatRichText(`[bold]5[/bold]. <span class="cyan-text">${event.choices[0]}</span>`);
    choice6Btn.innerHTML = formatRichText(`[bold]6[/bold]. <span class="cyan-text">${event.choices[1]}</span>`);

    eventPanel.classList.remove('hidden');
    menuPanel.classList.add('hidden'); // 隱藏菜單
}

function processEventChoice(choiceNum) {
    if (!currentEvent) return;

    const actualChoiceIdx = choiceNum - 5;
    
    if (actualChoiceIdx >= 0 && actualChoiceIdx < currentEvent.choices.length) {
        log(`你選擇了：[bold green]${currentEvent.choices[actualChoiceIdx]}[/bold green]`, true, true);
        const outcomeMsg = currentEvent.outcomes[actualChoiceIdx];
        log(outcomeMsg, true, true);

        // 處理結局事件
        if (currentEvent.type === "ending" && actualChoiceIdx === 0) {
            gameEndedByEvent = true;
            gameRunning = false;
            log("[bold green]你已挖通礦脈，遊戲結束！[/bold green]", true, true);
            setTimeout(showGameOverScreen, 500); // 延遲顯示結束畫面
            return;
        }

        // --- 處理簡化後的事件效果 ---
        if (currentEvent.reward && actualChoiceIdx === 0) {
            oreCount += currentEvent.reward;
            log(`額外獲得 [yellow]${currentEvent.reward}[/yellow] 礦石！`, true, true);
        }
        
        if (currentEvent.upgrade && actualChoiceIdx === 0) {
            multiplier *= 2;
            orePerMine = Math.floor(orePerMine * 2); // 確保是整數
            log("[bold yellow]你的工具升級了！產出翻倍！[/bold yellow]", true, true);
        }
        
        if (currentEvent.ore_per_mine_boost && actualChoiceIdx === currentEvent.ore_per_mine_boost.idx) {
            orePerMine += currentEvent.ore_per_mine_boost.value;
            log(`單次產出提升 [green]${currentEvent.ore_per_mine_boost.value}[/green]！`, true, true);
        }

        if (currentEvent.multiplier_boost && actualChoiceIdx === currentEvent.multiplier_boost.idx) {
            multiplier += currentEvent.multiplier_boost.value;
            log(`倍率提升 [cyan]${currentEvent.multiplier_boost.value.toFixed(1)}x[/cyan]！`, true, true);
        }
        
        if (currentEvent.ore_cost && actualChoiceIdx === currentEvent.ore_cost.idx) {
            const cost = currentEvent.ore_cost.cost;
            if (oreCount >= cost) {
                oreCount -= cost;
                log(`你花費 [yellow]${cost}[/yellow] 礦石加固了周圍。`, true, true);
            } else {
                log("[red]礦石不足，無法執行此操作。[/red]", true, true);
            }
        }
        
        currentEvent = null; // 事件處理完畢
        eventPanel.classList.add('hidden');
        menuPanel.classList.remove('hidden'); // 顯示菜單
        updateStatusDisplay();
    } else {
        log("[red]無效的事件選擇。[/red]", true, true);
    }
}

function mineOnce() {
    const gain = Math.floor(orePerMine * multiplier);
    oreCount += gain;
    log(`你挖到 [yellow]${gain}[/yellow] 顆礦石。總共：[yellow]${oreCount}[/yellow]`);
    updateStatusDisplay();
}

function handleMenuChoice(action) {
    switch (action) {
        case 1: // 升級工具
            if (oreCount >= 10) {
                oreCount -= 10;
                orePerMine += 1;
                log("你升級了工具！單次產出提升。", true);
            } else {
                log("[red]礦石不足，無法升級。[/red]", true);
            }
            break;
        case 2: // 查看狀態
            log("[dim]狀態已刷新。[/dim]", true);
            break;
        case 3: // 離開遊戲
            gameRunning = false;
            log("你離開了礦井。遊戲結束。", true);
            showGameOverScreen();
            break;
        case 4: // 查看紀錄
            showFullHistory();
            break;
    }
    updateStatusDisplay();
}

function showFullHistory() {
    let historyHtml = '<table><thead><tr><th>時間</th><th>紀錄</th></tr></thead><tbody>';
    if (history.length === 0) {
        historyHtml += '<tr><td colspan="2" class="dim-text center-text">目前沒有任何記錄。</td></tr>';
    } else {
        history.forEach(entry => {
            const timePartMatch = entry.text.match(/^\[(.*?)\]\s*(.*)/);
            if (timePartMatch) {
                historyHtml += `<tr><td class="dim-text">[${timePartMatch[1]}]</td><td>${formatRichText(timePartMatch[2])}</td></tr>`;
            } else {
                historyHtml += `<tr><td></td><td>${formatRichText(entry.text)}</td></tr>`;
            }
        });
    }
    historyHtml += '</tbody></table>';
    showModal('📜 完整遊戲紀錄', historyHtml);
}

function showGameOverScreen() {
    let finalMessage = `你的最終單次產出：<span class="green-text">${orePerMine}</span><br><br>`;
    
    let eventHistoryHtml = '<table><thead><tr><th>時間</th><th>事件記錄</th></tr></thead><tbody>';
    const eventRecords = history.filter(item => item.is_event);

    if (eventRecords.length === 0) {
        eventHistoryHtml += '<tr><td colspan="2" class="dim-text center-text">沒有山洞事件記錄。</td></tr>';
    } else {
        eventRecords.forEach(entry => {
            const timePartMatch = entry.text.match(/^\[(.*?)\]\s*(.*)/);
            if (timePartMatch) {
                eventHistoryHtml += `<tr><td class="dim-text">[${timePartMatch[1]}]</td><td>${formatRichText(timePartMatch[2])}</td></tr>`;
            } else {
                eventHistoryHtml += `<tr><td></td><td>${formatRichText(entry.text)}</td></tr>`;
            }
        });
    }
    eventHistoryHtml += '</tbody></table>';

    showModal('遊戲結束！', `<p class="center-text bold-text red-text">感謝遊玩！</p><p class="center-text">${finalMessage}</p><h2>📜 山洞事件記錄</h2>${eventHistoryHtml}`);
    // 關閉按鈕可以移除，因為遊戲已經結束了
    modalCloseBtn.onclick = () => {
        closeModal();
        // 如果想允許玩家再次開始，可以在這裡加入重新整理頁面的邏輯
        // location.reload(); 
    };
    modalCloseBtn.textContent = '確定'; // 改變按鈕文字
}


// --- 遊戲主循環 (使用 requestAnimationFrame 或 setInterval) ---
let gameLoopInterval;

function gameLoop() {
    if (!gameRunning) {
        clearInterval(gameLoopInterval); // 停止遊戲循環
        return;
    }

    const now = Date.now();

    // 自動挖礦
    if (now - lastMineTime >= mineInterval * 1000) {
        mineOnce();
        lastMineTime = now;
    }

    // 事件觸發
    if (now >= nextEventTime && currentEvent === null) {
        if (!firstEventTriggered) {
            log("[bold red]第一次事件即將觸發！[/bold red]", true);
            triggerRandomEvent();
            firstEventTriggered = true;
        } else if (Math.random() < eventChance) {
            triggerRandomEvent();
        } else {
            log("[dim]沒有事件發生，繼續挖礦...[/dim]", true);
        }
        nextEventTime = now + (Math.floor(Math.random() * (eventIntervalMax - eventIntervalMin + 1)) + eventIntervalMin) * 1000;
    }

    // 更新顯示 (每 100 毫秒更新一次，避免過度渲染)
    updateStatusDisplay();
}

// --- 事件監聽器 (處理用戶輸入) ---
choice5Btn.addEventListener('click', () => processEventChoice(5));
choice6Btn.addEventListener('click', () => processEventChoice(6));

menuUpgradeBtn.addEventListener('click', () => handleMenuChoice(1));
menuStatusBtn.addEventListener('click', () => handleMenuChoice(2));
menuExitBtn.addEventListener('click', () => handleMenuChoice(3));
menuViewLogBtn.addEventListener('click', () => handleMenuChoice(4));
modalCloseBtn.addEventListener('click', closeModal);


// 初始化遊戲
function initGame() {
    log("🪨 [bold green]歡迎來到《Codexu3 礦井》！[/bold green]", true);
    log("遊戲將自動進行挖礦與事件探索。", false);
    log("事件發生時請做出選擇。在非事件期間，點擊按鈕或按下 Enter 鍵開啟菜單。", false);
    
    updateStatusDisplay();
    updateHistorySnippet();
    
    // 開始遊戲循環
    gameLoopInterval = setInterval(gameLoop, 100); // 每 100 毫秒執行一次遊戲邏輯
}

// 監聽鍵盤事件來打開菜單
document.addEventListener('keydown', (event) => {
    // 如果有事件正在顯示，優先處理事件選擇
    if (currentEvent) {
        if (event.key === '5') {
            processEventChoice(5);
        } else if (event.key === '6') {
            processEventChoice(6);
        }
    } else {
        // 如果沒有事件，且按下 Enter 鍵
        if (event.key === 'Enter') {
            // 切換菜單顯示狀態，或者簡單地讓菜單一直可見，只處理點擊
            // 目前菜單是常駐的，所以這裡不需要特別操作，只是捕獲 Enter 鍵的語義
            // 如果你希望 Enter 鍵彈出一個更互動的菜單，可以在這裡實現
            log("[dim]已返回遊戲自動進程。[/dim]", true); // 這裡只是模擬原 Python 行為
        }
    }
});

// 開始遊戲
initGame();