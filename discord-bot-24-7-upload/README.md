# Discord Bot Python

Bot Discord co ban viet bang Python voi `discord.py`, co the chat tu nhien nhu nguoi that.

## Cai dat

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Cau hinh

1. Tao file `.env` tu `.env.example`
2. Dien token bot Discord vao `DISCORD_BOT_TOKEN`
3. Dien API key vao `OPENAI_API_KEY`

## Chay bot

```powershell
.venv\Scripts\Activate.ps1
python bot.py
```

## Chay 24/7 tren Render + UptimeRobot

Project da co san keep-alive endpoint:

- `/`
- `/health`

Render se tu dung bien `PORT`, bot se bind web server vao `0.0.0.0`.

### 1. Dua project len GitHub

Khong upload file `.env`. File `.gitignore` da chan `.env` va `.venv`.

### 2. Tao Web Service tren Render

- New + -> Web Service
- Connect repo GitHub cua bot
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot.py`
- Environment: Python

Them Environment Variables:

```text
DISCORD_BOT_TOKEN=token_bot_discord_cua_ban
OPENAI_API_KEY=api_key_openai_cua_ban
OPENAI_MODEL=gpt-5.2
BOT_PREFIX=!
KEEP_ALIVE_HOST=0.0.0.0
```

Sau khi deploy xong, Render se cho link dang:

```text
https://ten-service.onrender.com
```

Kiem tra health:

```text
https://ten-service.onrender.com/health
```

### 3. Tao monitor tren UptimeRobot

- Monitor Type: HTTP(s)
- Friendly Name: Discord SKG Bot
- URL: `https://ten-service.onrender.com/health`
- Monitoring Interval: 5 minutes

Neu `/health` tra ve JSON co `status: online` la duoc.

## Lenh san co

- `!ping`
- `!help`
- `!chat <noi_dung>`
- `!reset`
- `!join`
- `!leave`
- `!kick @ten_nguoi_dung [ly_do]`
- `!ban @ten_nguoi_dung [ly_do]`
- `!taixiu <tai|xiu>`
- `!taixiuroom <so_tien_cuoc> [thoi_gian]`
- `!coinflip`
- `!meme`
- `!memespam [so_luong_toi_da_100]`
- `!roast @ten`
- `!roll [so_toi_da]`
- `!daily`
- `!give @ten <so_tien>`
- `!loan @ten <so_tien>`
- `!balance [@ten]`
- `!profile [@ten]`
- `!debt [@ten]`
- `!repay @ten <so_tien>`

## Luu y

- Trong Discord Developer Portal, bat `Message Content Intent` neu muon dung lenh text thong thuong.
- Bot se tra loi khi ban:
  - dung `!chat <noi_dung>`
  - mention bot trong kenh
  - reply vao tin nhan cua bot
- Bot giu bo nho ngan theo tung kenh de noi chuyen tu nhien hon.
- De vao voice, bot can quyen `Connect` va `Speak` trong server.
- De kick/ban, nguoi dung va bot deu can quyen tuong ung trong server.
- He thong tien ao duoc luu trong file `economy.json`, co so du khoi tao va nhan daily moi ngay.
- Neu ai do bi tag trong kenh ma sau 5 phut khong co ai reply vao dung tin nhan do, bot se gui mot cau ca khia nhe.
- Meme hien dang dung danh sach anh truc tiep on dinh de Discord hien thi tot. Neu muon lay truc tiep tu Pinterest, can lam them bo xu ly rieng cho link pin.
