"""Generic install accessibility; add tests of the actual application separately."""
def test_install_is_user_initiated(page):
    page.goto('/')
    panel = page.locator('#lab-install-panel')
    assert panel.is_hidden()
    assert page.locator('#lab-install-open').is_visible()
    page.locator('#lab-install-open').click()
    assert panel.is_visible()
    page.locator('#lab-install-later').click()
    assert panel.is_hidden()
    page.reload()
    assert panel.is_hidden()
    page.locator('#lab-install-open').click()
    assert panel.is_visible()
