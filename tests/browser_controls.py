"""Navigate controls now housed in the playground menus."""
def click_tool(page, selector):
    if not page.locator(selector).is_visible():
        page.locator('#replay-tools > summary').click()
    page.locator(selector).click()


def select_setting(page, selector, value):
    menu = '#replay-tools > summary' if selector.startswith('#replay-') else '.playground-settings > summary'
    if not page.locator(selector).is_visible():
        page.locator(menu).click()
    page.locator(selector).select_option(value)
    if page.locator(menu).evaluate('(el)=>el.parentElement.open'):
        page.locator(menu).click()
