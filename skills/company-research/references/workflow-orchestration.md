# 研究流程的執行與觀測
只在要自動化、續跑或評估研究流程時讀本篇。先檢查現有repo、工具、授權與能力，不因方法提到LangChain、LangGraph或Langfuse就宣稱已安裝或可呼叫；不得把目前對話可用模型視為已取得獨立API憑證。

## 最小架構
沿既有來源／報告bundle與確定性函式，先建run manifest與階段輸出。LangGraph是有需要時的checkpoint／分支／人工等待候選，LangChain是可選介接，Langfuse是可選觀測。三者不必綁用；也不預設新增圖資料庫、向量庫或多agent supervisor。框架版本、價格、API和相容性在實作時查官方文件並鎖定；不把舊範例當當前支援。

記run/attempt、固定基線與來源、schema/workflow/code/parser、prompt/model/tool版本、輸入輸出artifact hash、驗證／審查、預算及停止原因。原文資料庫、checkpoint、trace分工：trace不能替代證據，checkpoint不是canonical研究。檢索或衍生wiki是導航，重要主張仍回到已核對原文。

## 恢復與人機責任
先盤點覆蓋→固定合法來源→解析並核對日期／單位→提取候選→驗證引述與公式→查反證→人判斷→生成待接受版本。可跳過與當次增量無關的階段，但不能跳過受影響的驗證。
checkpoint恢復、node retry及replay可能重跑呼叫，所有副作用要有idempotency key與receipt。已授權的範圍持續有效；只在新外部權限、費用、資料目的地或真正需要人的判斷時等待，不把每個節點變成重新要批准。
暫時性錯誤有界重試；來源拒絕、schema錯誤與語義矛盾轉為可解釋狀態。取消或達預算上限就保存部分成果。prompt／parser／來源修訂只使相關下游失效；並行run的基線變更須重評，不能覆寫他人接受的新版本。人工修正append另存，模型不能自動取代。

## 重現、評估及隱私
分清固定證據可追溯、確定性數值可重算、LLM過程可稽核；同prompt/model設定不保證日後逐字相同。接受的引述要能精確匹配來源，數值要能重算，as-of不得偷渡後知資料；缺Q&A不能標完整。先用有標準答案的合成／合法公開fixture檢查失敗、恢復、空資料、修訂及重複副作用。LLM judge僅輔助找問題，不能當獨立真相或agent投票結案。

預設本機run metadata；不自動啟用LangSmith／Langfuse雲端trace或上傳private dataset。外送若獲准，以必要欄位白名單檢查span／event／resource／media／errors及其他exporters；單純遮input/output或hash不等於匿名。自架亦需明定保留、刪除、存取、備份與對外連線。
成本記全run（含子工作、重試與judge），先用去重與增量減量，unknown usage不記0。執行前訂token與金額上限；未批准的新付費服務不支出。付款、來源使用權、模型資料外送與trace長期儲存各自判定，開源框架不會自動取得這些權利。
