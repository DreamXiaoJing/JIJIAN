// ==UserScript==
// @name         Beatsource 手动点击下载 AAC
// @namespace    https://github.com/DreamXiaoJing
// @version      3.1
// @description  页面右上角出现下载按钮，点击后整段 AAC 保存到本地
// @author       wqw
// @match        https://www.beatsource.com/track/*
// @grant        GM_notification
// ==/UserScript==

(() => {
    'use strict';

    /* ---------- 工具 ---------- */
    const ab2buf = ab => new Uint8Array(ab);
    const buf2ab = buf => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    const hex2ab = hex => new Uint8Array(hex.match(/.{2}/g).map(b => parseInt(b, 16)));
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    async function decryptAES(buf, keyBuf, ivHex) {
        const key = await crypto.subtle.importKey('raw', keyBuf, { name: 'AES-CBC' }, false, ['decrypt']);
        const iv  = hex2ab(ivHex || '00000000000000000000000000000000');
        return ab2buf(await crypto.subtle.decrypt({ name: 'AES-CBC', iv }, key, buf));
    }

    async function dl(url) {
        const r = await fetch(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.beatsource.com',
                'Origin': 'https://www.beatsource.com'
            }
        });
        return ab2buf(await r.arrayBuffer());
    }

    function parseM3U8(text, base) {
        const lines = text.trim().split('\n');
        const segs = [];
        let keyUri = null, iv = null;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('#EXT-X-KEY')) {
                const u = line.match(/URI="([^"]+)"/), v = line.match(/IV=0x([0-9a-fA-F]+)/);
                if (u) keyUri = new URL(u[1], base).href;
                if (v) iv = v[1];
            } else if (line.startsWith('#EXTINF') && i + 1 < lines.length) {
                const url = new URL(lines[i + 1].trim(), base).href;
                segs.push(url);
            }
        }
        return { segs, keyUri, iv };
    }

    /* ---------- 拿当前曲目数据（每次都重新解析） ---------- */
    async function getCurrentTrack() {
        for (let i = 0; i < 50; i++) {
            const raw = document.getElementById('__NEXT_DATA__')?.innerHTML;
            if (raw) {
                try {
                    const nextData = JSON.parse(raw);
                    const t = nextData?.props?.pageProps?.track;
                    if (t) return t;
                } catch {}
            }
            await sleep(300);
        }
        throw new Error('未找到曲目数据');
    }

    /* ---------- 下载逻辑 ---------- */
    async function downloadAAC() {
        const btn = document.getElementById('btsrc-dl-btn');
        btn.disabled = true;
        btn.textContent = '⬇ 准备中…';

        try {
            /* 1. 每次都重新拿当前这首歌的数据 */
            const track = await getCurrentTrack();
            const token = JSON.parse(localStorage.btsrcSession || '{}').access_token;
            if (!token) throw new Error('请先登录一次');

            /* 2. 获取 m3u8 */
            const api = `https://api.beatsource.com/v4/catalog/tracks/${track.id}/stream`;
            const stream = await (await fetch(`${api}?start=${track.sample_start_ms}&end=${track.sample_end_ms}`, {
                headers: { Authorization: `Bearer ${token}` }
            })).json();
            const m3u8Url = stream.stream_url;
            if (!m3u8Url) throw new Error('无地址');

            /* 3. 解析索引 */
            const base = m3u8Url.slice(0, m3u8Url.lastIndexOf('/') + 1);
            const m3u8Text = new TextDecoder().decode(await dl(m3u8Url));
            const { segs, keyUri, iv } = parseM3U8(m3u8Text, base);
            if (!segs.length) throw new Error('无片段');

            /* 4. 下载密钥 */
            let keyBuf = null;
            if (keyUri) keyBuf = await dl(keyUri);

            /* 5. 下载片段 */
            btn.textContent = `⬇ 0/${segs.length}`;
            const chunks = [];
            for (let i = 0; i < segs.length; i++) {
                const buf = await dl(segs[i]);
                chunks.push(keyBuf ? await decryptAES(buf2ab(buf), keyBuf, iv) : buf);
                btn.textContent = `⬇ ${i + 1}/${segs.length}`;
            }

            /* 6. 合并 */
            const totalLen = chunks.reduce((a, c) => a + c.length, 0);
            const merged = new Uint8Array(totalLen);
            let off = 0;
            chunks.forEach(c => { merged.set(c, off); off += c.length; });

            /* 7. 保存文件 */
            const blob = new Blob([merged], { type: 'audio/aac' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${track.artists.map(x => x.name).join(', ')} - ${track.title}.aac`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(a.href);
            a.remove();
            GM_notification('AAC 已保存！', 'Beatsource');
        } catch (e) {
            GM_notification('下载失败：' + e.message, 'Beatsource');
            console.error(e);
        } finally {
            btn.disabled = false;
            btn.textContent = '⬇ 下载';
        }
    }

    /* ---------- 插入按钮 ---------- */
    function insertButton() {
        if (document.getElementById('btsrc-dl-btn')) return;
        const btn = document.createElement('button');
        btn.id = 'btsrc-dl-btn';
        btn.textContent = '⬇ 下载';
        btn.title = '下载整段 AAC';
        btn.style.position = 'fixed';
        btn.style.top = '20px';
        btn.style.right = '20px';
        btn.style.zIndex = '9999';
        btn.style.padding = '6px 12px';
        btn.style.background = '#1db954';
        btn.style.color = '#fff';
        btn.style.border = 'none';
        btn.style.borderRadius = '4px';
        btn.style.cursor = 'pointer';
        btn.addEventListener('click', downloadAAC);
        document.body.appendChild(btn);
    }

    /* ---------- SPA 兼容 ---------- */
    let last = location.href;
    const observer = new MutationObserver(() => {
        if (location.href !== last) {
            last = location.href;
            if (last.includes('/track/')) setTimeout(insertButton, 1500);
        }
    });
    observer.observe(document, { subtree: true, childList: true });

    /* ---------- 首次进入 ---------- */
    if (location.href.includes('/track/')) setTimeout(insertButton, 1500);
})();