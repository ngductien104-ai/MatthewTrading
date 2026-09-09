# Nhac them tin hieu truoc khi ban tin chay.
#
# Vi sao ton tai: lich chay luc 11h40 va 15h10 la tien trinh khong tuong tac -
# no khong hoi duoc ai. Nen viec hoi duoc tach ra thanh mot lan nhac RIENG,
# chay som hon 15 phut, de con kip them tin hieu vao so truoc khi ban tin dung.
#
#   ask_signals.ps1 morning   -> chay 11h25
#   ask_signals.ps1 close     -> chay 14h55
#
# Neu so da co tin hieu ghi HOM NAY thi khong lam phien nua.

param([string]$Session = "close")

$repo   = "C:\Users\VVVZV\MatthewTrading"
$ledger = Join-Path $repo "agent\data\signals.yaml"
$today  = Get-Date -Format "yyyy-MM-dd"
$label  = if ($Session -eq "morning") { "phien sang (11h40)" } else { "dong cua (15h10)" }

$hasToday = $false
if (Test-Path $ledger) {
  $hasToday = (Select-String -Path $ledger -Pattern "date:\s*$today" -Quiet) -eq $true
}
if ($hasToday) { exit 0 }   # da co tin hieu hom nay, khong nhac lai

$count = 0
if (Test-Path $ledger) {
  $count = (Select-String -Path $ledger -Pattern "^- symbol:" -AllMatches).Count
}

$title = "Ban tin $label sap chay"
$body  = if ($count -eq 0) {
  "So khuyen nghi dang TRONG. Hom nay anh co ma nao khuyen nghi khong? Neu co, bao Claude: ma - hanh dong - vung mua - cat lo - chot loi."
} else {
  "So dang co $count tin hieu, chua co muc nao ghi hom nay. Them ma moi neu can."
}

# Toast cua Windows. Neu API toast khong dung duoc thi lui ve balloon khay he
# thong - im lang tuyet doi la ket qua te nhat, vi khi do khong ai duoc hoi.
$shown = $false
try {
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
  $tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
           [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
  $texts = $tpl.GetElementsByTagName("text")
  $texts.Item(0).AppendChild($tpl.CreateTextNode($title)) | Out-Null
  $texts.Item(1).AppendChild($tpl.CreateTextNode($body))  | Out-Null
  $toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(
    "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App").Show($toast)
  $shown = $true
} catch { $shown = $false }

if (-not $shown) {
  try {
    Add-Type -AssemblyName System.Windows.Forms
    $ni = New-Object System.Windows.Forms.NotifyIcon
    $ni.Icon = [System.Drawing.SystemIcons]::Information
    $ni.BalloonTipTitle = $title
    $ni.BalloonTipText  = $body
    $ni.Visible = $true
    $ni.ShowBalloonTip(20000)
    Start-Sleep -Seconds 12
    $ni.Dispose()
    $shown = $true
  } catch { $shown = $false }
}

# Ghi ra dia bat ke toast co hien hay khong, de con lan vet lai duoc.
$logDir = Join-Path $repo "_market_logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$state = if ($shown) { "da nhac" } else { "KHONG hien duoc thong bao" }
Add-Content -Path (Join-Path $logDir "ask_signals.log") -Encoding utf8 `
  -Value "[$stamp] $Session - $count tin hieu trong so - $state"
