(() => {
    'use strict';
    const menu = document.querySelector('[data-nav-toggle]');
    const backdrop = document.querySelector('[data-nav-close]');
    const sidebar = document.getElementById('workspace-nav');
    const setNavigation = open => {
        document.body.classList.toggle('nav-open', open);
        menu?.setAttribute('aria-expanded', String(open));
        if (backdrop) backdrop.hidden = !open;
        if (sidebar && window.matchMedia('(max-width: 760px)').matches) sidebar.inert = !open;
        if (open) sidebar?.querySelector('a')?.focus();
        else menu?.focus();
    };
    menu?.addEventListener('click', () => setNavigation(!document.body.classList.contains('nav-open')));
    backdrop?.addEventListener('click', () => setNavigation(false));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && document.body.classList.contains('nav-open')) setNavigation(false);
        if (event.key === 'Tab' && document.body.classList.contains('nav-open') && sidebar) {
            const links = [...sidebar.querySelectorAll('a, button')];
            const first = links[0], last = links[links.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });
    const navMedia = window.matchMedia('(max-width: 760px)');
    const syncNavigation = () => {
        if (sidebar) sidebar.inert = navMedia.matches && !document.body.classList.contains('nav-open');
        if (!navMedia.matches) { document.body.classList.remove('nav-open'); if (backdrop) backdrop.hidden = true; menu?.setAttribute('aria-expanded', 'false'); }
    };
    navMedia.addEventListener('change', syncNavigation);
    syncNavigation();

    const viewButtons = document.querySelectorAll('[data-view]');
    const panels = document.querySelectorAll('[data-view-panel]');
    if (viewButtons.length) {
        document.body.classList.add('js-views');
        const selectView = view => {
            viewButtons.forEach(button => { const selected = button.dataset.view === view; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); });
            panels.forEach(panel => { panel.hidden = panel.dataset.viewPanel !== view; });
            const url = new URL(window.location.href);
            if (view === 'list') url.searchParams.set('view', 'list'); else url.searchParams.delete('view');
            history.replaceState(null, '', url);
            const filters = document.querySelector('.filter-bar');
            let viewInput = filters?.querySelector('[name=view]');
            if (filters && !viewInput) { viewInput = document.createElement('input'); viewInput.type = 'hidden'; viewInput.name = 'view'; filters.append(viewInput); }
            if (viewInput) viewInput.value = view;
            document.querySelectorAll('.month-navigation a').forEach(link => {
                const target = new URL(link.href);
                if (view === 'list') target.searchParams.set('view', view); else target.searchParams.delete('view');
                link.href = target;
            });
        };
        selectView(new URLSearchParams(location.search).get('view') === 'list' ? 'list' : 'calendar');
        viewButtons.forEach(button => button.addEventListener('click', () => selectView(button.dataset.view)));
    }
    const weeks = [...document.querySelectorAll('[data-week]')];
    const weekMedia = window.matchMedia('(max-width: 480px)');
    let currentWeek = Math.max(0, weeks.findIndex(week => week.querySelector('.calendar-today')));
    const showWeek = () => {
        weeks.forEach((week, index) => { week.hidden = weekMedia.matches && index !== currentWeek; });
        const days = weeks[currentWeek]?.querySelectorAll('.day-number');
        const label = document.querySelector('[data-week-label]');
        if (label && days?.length) label.textContent = `${days[0].textContent} – ${days[days.length - 1].textContent} / ${document.getElementById('calendar-heading').textContent.trim()}`;
        const previous = document.querySelector('[data-week-prev]'), next = document.querySelector('[data-week-next]');
        if (previous) previous.disabled = currentWeek === 0;
        if (next) next.disabled = currentWeek === weeks.length - 1;
    };
    document.querySelector('[data-week-prev]')?.addEventListener('click', () => { currentWeek = Math.max(0, currentWeek - 1); showWeek(); });
    document.querySelector('[data-week-next]')?.addEventListener('click', () => { currentWeek = Math.min(weeks.length - 1, currentWeek + 1); showWeek(); });
    weekMedia.addEventListener('change', showWeek);
    showWeek();

    const itemType = document.querySelector('[data-item-form]');
    if (itemType) {
        const updatePrice = () => {
            const type = itemType.querySelector('[name=item_type]:checked')?.value;
            itemType.querySelectorAll('[data-price-section]').forEach(section => { section.hidden = section.dataset.priceSection !== type; });
        };
        itemType.addEventListener('change', updatePrice);
        updatePrice();
    }
    const payment = document.querySelector('[data-payment-form]');
    if (payment) {
        const updatePayment = () => {
            const unpaid = payment.querySelector('[name=payment_method]').value === 'unpaid';
            payment.querySelectorAll('[data-payment-section]').forEach(section => {
                const visible = section.dataset.paymentSection === (unpaid ? 'unpaid' : 'paid');
                section.hidden = !visible;
                section.querySelectorAll('input').forEach(input => { input.disabled = !visible; input.required = visible; });
            });
        };
        payment.querySelector('[name=payment_method]').addEventListener('change', updatePayment);
        updatePayment();
    }
})();
