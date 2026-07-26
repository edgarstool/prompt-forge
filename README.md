# Prompt Forge

> Turn vague ideas into executable prompts.
>
> 把模糊的想法，鍛造成可以交給 AI 執行的任務。

Prompt Forge 是一個面向多種 AI Agent 的 Prompt 生產系統。它不是 Prompt 收藏夾，而是一條可測試、可改良、可交付的任務鍛造流程。

## 產品目標

使用者只需要描述目標，Prompt Forge 應該能：

1. 判斷任務類型與真正意圖。
2. 選擇適合的 Agent、工具與資料來源。
3. 補上合理假設，而不是不斷反問。
4. 產出可以直接複製執行的完整 Prompt。
5. 內建驗收、停止條件與必要的回復方式。
6. 在涉及 library、SDK、API、CLI 或 framework 時，透過 Context7 取得版本相符的最新文件。

## 產品原則

- **先給可用版本，再一起修。**
- **只有真正阻塞或高風險時才提問。**
- **Prompt 是施工單，不是理論課。**
- **能由確定性工具完成的事，不交給模型猜。**
- **安全措施要與風險成比例，不用棉被包住螺絲起子。**
- **每次交付都應可驗收、可比較、可停止。**

## v0.1 範圍

第一版先完成四件事：

- Prompt Router：判斷任務類型與建議執行者。
- Prompt Composer：把需求組成完整可執行 Prompt。
- Context7 Policy：技術任務自動加入最新文件查核。
- Prompt Evaluation：用固定測試判斷輸出是否完整、簡潔、可執行。

暫時不做：

- 完整聊天產品
- 多租戶與帳號系統
- 自動執行 production 變更
- Prompt 市集
- 複雜前端介面

## 預計結構

```text
prompt-forge/
├─ docs/          # 產品設計、決策與交付流程
├─ prompts/       # 可組合的 Prompt 模板
├─ routers/       # 任務分類與工具路由規則
├─ skills/        # 特定 Agent / 領域能力包
├─ evaluators/    # Prompt 品質檢查規則
├─ examples/      # 真實輸入與預期輸出
├─ tests/         # 驗收案例
└─ adapters/      # Context7、GitHub 等外部來源接口
```

## 目前狀態

**Foundation / 產品地基建立中。**

先定義產品要解決什麼、如何從設計走到交付，再進入可執行原型。

## 專案角色

- **產品擁有者：** 王世鈞（Edgar）／德德
- **協作方式：** AI 提議與施工，Edgar 保留方向決定權；任何設計都可以根據實際使用推翻重做。

## License

尚未定案。正式發布前再選擇合適授權方式。
