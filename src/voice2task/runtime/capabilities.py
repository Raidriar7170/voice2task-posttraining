from __future__ import annotations

from dataclasses import dataclass

from voice2task.runtime.models import ActionKind

REGISTRY_VERSION = "controlled-demo-v1"


@dataclass(frozen=True)
class Capability:
    capability_id: str
    path: str
    route: str
    locators: dict[str, str]
    allowed_actions: frozenset[ActionKind]
    aliases: frozenset[str]
    verifier: str
    requires_confirmation: bool = False
    heading: str | None = None
    expected_values: dict[str, str] | None = None


CAPABILITY_REGISTRY: dict[str, Capability] = {
    "demo_search": Capability(
        capability_id="demo_search",
        path="/sandbox/search",
        route="search_web",
        locators={
            "query_input": '[data-testid="query-input"]',
            "search_button": '[data-testid="search-button"]',
            "results": '[data-testid="results"]',
        },
        allowed_actions=frozenset({ActionKind.NAVIGATE, ActionKind.FILL, ActionKind.CLICK}),
        aliases=frozenset({"search"}),
        verifier="results_contain_query",
        heading="受控搜索",
    ),
    "demo_help": Capability(
        capability_id="demo_help",
        path="/sandbox/help",
        route="open_url",
        locators={"heading": '[data-testid="help-heading"]'},
        allowed_actions=frozenset({ActionKind.NAVIGATE}),
        aliases=frozenset({"帮助中心", "https://help.example.com"}),
        verifier="url_and_heading",
        heading="Voice2Task 帮助中心",
    ),
    "demo_product": Capability(
        capability_id="demo_product",
        path="/sandbox/product",
        route="extract_page",
        locators={"product_price": '[data-testid="product-price"]'},
        allowed_actions=frozenset({ActionKind.NAVIGATE, ActionKind.EXTRACT_TEXT}),
        aliases=frozenset({"商品价格"}),
        verifier="extracted_text_equals_dom",
        heading="演示商品",
        expected_values={"product_price": "¥199.00"},
    ),
    "demo_profile_form": Capability(
        capability_id="demo_profile_form",
        path="/sandbox/profile",
        route="fill_form",
        locators={
            "email_input": '[data-testid="email-input"]',
            "save_button": '[data-testid="save-button"]',
            "success_message": '[data-testid="success-message"]',
        },
        allowed_actions=frozenset({ActionKind.NAVIGATE, ActionKind.FILL}),
        aliases=frozenset({"邮箱", "email"}),
        verifier="field_value_equals",
        requires_confirmation=True,
        heading="本地 Profile 表单",
    ),
}
