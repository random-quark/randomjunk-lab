"""Keep and extend with tests of the requested application's behavior."""
def test_install_offer_and_dismissal(page):
    page.goto('/')
    panel = page.locator('#lab-install-panel')
    assert panel.is_visible()
    page.locator('#lab-install-later').click()
    assert panel.is_hidden()
    page.reload()
    assert panel.is_hidden()
    page.locator('#lab-install-open').click()
    assert panel.is_visible()
