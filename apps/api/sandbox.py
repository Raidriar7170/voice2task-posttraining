from __future__ import annotations

from html import escape

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["sandbox"])


_STYLE = """
*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#e5edf7;font:16px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:48px auto;padding:28px;background:#141e2e;border:1px solid #334155;border-radius:16px}
h1{margin-top:0;color:#f8fafc}label{display:block;margin:18px 0 8px;color:#b8c8dc}
input{width:100%;padding:12px;border:1px solid #64748b;border-radius:8px;background:#09111f;color:#f8fafc}
button{margin-top:14px;padding:11px 18px;border:0;border-radius:8px;background:#36d399;color:#06281c;font-weight:700}
.card{margin-top:18px;padding:16px;border-left:4px solid #38bdf8;background:#0d1727}.muted{color:#9fb0c4}
.price{font-size:2rem;color:#fbbf24;font-weight:800}
.badge{display:inline-block;padding:4px 9px;border-radius:99px;background:#23314a;color:#a7f3d0}
"""


def _page(title: str, body: str) -> HTMLResponse:
    html = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)}</title>"
        f"<style>{_STYLE}</style></head><body><main>{body}</main></body></html>"
    )
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


@router.get("/sandbox/search", response_class=HTMLResponse)
async def search_page(q: str = Query(default="", max_length=200)) -> HTMLResponse:
    safe_query = escape(q)
    result = ""
    if q:
        result = (
            '<section class="card" data-testid="results">'
            f"<strong>受控结果：{safe_query}</strong>"
            '<p class="muted">这是 localhost fixture 的确定性结果，不代表真实互联网搜索。</p>'
            "</section>"
        )
    body = (
        '<span class="badge">localhost sandbox</span><h1>受控搜索</h1>'
        '<form method="get" action="/sandbox/search">'
        '<label for="query">搜索词</label>'
        f'<input id="query" name="q" data-testid="query-input" value="{safe_query}" autocomplete="off">'
        '<button type="submit" data-testid="search-button">运行本地搜索</button>'
        f"</form>{result}"
    )
    return _page("受控搜索", body)


@router.get("/sandbox/help", response_class=HTMLResponse)
async def help_page() -> HTMLResponse:
    return _page(
        "Voice2Task 帮助中心",
        '<span class="badge">localhost sandbox</span>'
        '<h1 data-testid="help-heading">Voice2Task 帮助中心</h1>'
        '<p>这里演示受控导航。页面完全由本地 FastAPI 提供。</p>',
    )


@router.get("/sandbox/product", response_class=HTMLResponse)
async def product_page() -> HTMLResponse:
    return _page(
        "演示商品",
        '<span class="badge">localhost sandbox</span><h1>演示商品</h1>'
        '<p class="muted">固定 fixture 商品，用于确定性 DOM 提取。</p>'
        '<div class="price" data-testid="product-price">¥199.00</div>',
    )


@router.get("/sandbox/profile", response_class=HTMLResponse)
async def profile_page() -> HTMLResponse:
    return _page(
        "本地 Profile 表单",
        '<span class="badge">localhost sandbox</span><h1>本地 Profile 表单</h1>'
        '<p class="muted">仅填写本地 DOM；Demo 不保存或提交该值。</p>'
        '<label for="email">邮箱</label>'
        '<input id="email" type="email" data-testid="email-input" value="" autocomplete="off">'
        '<button type="button" data-testid="save-button" disabled>Demo 不提交</button>'
        '<p data-testid="success-message" class="muted">尚未提交</p>',
    )
