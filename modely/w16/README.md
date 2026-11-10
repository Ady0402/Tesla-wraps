# Mercedes-AMG F1 W16 致敬車皮（舊款 Model Y）

以 2025 年 Mercedes-AMG PETRONAS F1 車隊 W16 E Performance（63 號）塗裝為靈感的三款自訂車皮，適用 **舊款 Model Y**（本儲存庫的 [`modely/`](../) 模板）。

<a href="preview/compare.png"><img src="preview/compare.png" width="900"/></a>

| | 檔案 | 風格 |
| --- | --- | --- |
| **A** | [`W16_Silver_Arrow.png`](W16_Silver_Arrow.png) | 簡潔版：銀色車頭、前門 63 號碼牌與 PETRONAS、青綠色門檻線，後門起漸層轉黑並鋪滿三芒星 |
| **B** | [`W16_Race_Livery.png`](W16_Race_Livery.png) | 賽道版：青綠色斜帶與流線、黑色側箱、進氣口斜槓、大型 PETRONAS、C 柱號碼圓牌與贊助商字樣 |
| **C** | [`W16_Black_Arrow.png`](W16_Black_Arrow.png) | 暗黑版：碳黑車身、銀色車鼻化為星陣、雙青綠流線與大型 63 |

各版本的完整展開預覽在 [`preview/`](preview/)（`*_sheet.png` 為各面板展開圖，`*_3q.png` 為貼到 Tesla 官方渲染圖上的示意）。

## 安裝

1. 下載想要的 PNG（可以三個都放，最多 10 個）。
2. 傳到車上，二擇一：
   * **手機 App**（4.59.0 以上）：Creations → Wrap → Upload
   * **USB 隨身碟**：格式化為 exFAT / FAT32 / ext3 / ext4，在根目錄建立 `Wraps` 資料夾，把 PNG 放進去（隨身碟內不要有地圖或韌體更新檔）
3. 車上：Toybox → Paint Shop → Wraps 分頁套用。

## 符合 Tesla 規則

| 規則 | 本組檔案 |
| --- | --- |
| PNG 格式 | PNG、8-bit RGBA、非交錯 |
| 解析度 512–1024 px | 1024 × 1024（與模板相同） |
| 檔案大小 ≤ 1 MB | 約 150–200 kB |
| 檔名僅英數、底線、連字號、空白，≤ 30 字元 | `W16_Silver_Arrow.png` 等，最長 20 字元（含副檔名） |
| 只塗模板白色區域 | 透明度與官方 `template.png` 完全一致 |

可用 `python3 tools/check.py modely/w16/*.png` 重新驗證。

## 想自己改

車皮是由 [`tools/`](../../tools/) 裡的程式產生的（說明見 [`tools/README.md`](../../tools/README.md)）：

```bash
bash tools/setup.sh          # 第一次：安裝字型與 PNG 工具（Debian/Ubuntu）
python3 tools/build.py       # 重新產生三個版本與預覽
```

例如想換成 12 號，把 `tools/designs/w16_a.py`（或 `w16_b.py`、`w16_c.py`）裡的 `NUMBER = "63"` 改成 `"12"` 再重建即可。

## 注意

* 預覽圖是依模板反推的近似示意，並非 Tesla 的 3D 渲染；實際效果請以車機或 App 為準。
* 車窗、玻璃車頂、輪圈與燈具不屬於可塗範圍。
* 這是粉絲致敬作品，僅供個人使用；Mercedes-AMG、PETRONAS 及各贊助商名稱與標誌為其各自所有者之商標。
