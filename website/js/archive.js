document.addEventListener('DOMContentLoaded', () => {
    loadNewsletters();
    setupSearch();
});

let allNewsletters = [];
let displayedNewsletters = [];

function loadNewsletters() {
    fetch('/newsletters.json')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(data => {
            allNewsletters = data.sort((a, b) => new Date(b.date) - new Date(a.date));
            displayedNewsletters = [...allNewsletters];
            renderNewsletters();
            updateCount();
        })
        .catch(error => {
            console.error('Error loading newsletters:', error);
            showError();
        });
}

function setupSearch() {
    const searchInput = document.getElementById('search-newsletters');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(e.target.value.toLowerCase().trim());
        }, 300);
    });
}

function performSearch(query) {
    if (!query) {
        displayedNewsletters = [...allNewsletters];
    } else {
        displayedNewsletters = allNewsletters.filter(newsletter => {
            const searchableText = [
                newsletter.title.toLowerCase(),
                newsletter.date,
                `issue ${newsletter.issue}`,
                `#${newsletter.issue}`
            ].join(' ');
            return searchableText.includes(query);
        });
    }
    renderNewsletters();
    updateCount();
}

function renderNewsletters() {
    const container = document.getElementById('newsletter-list');
    if (!container) return;

    if (displayedNewsletters.length === 0) {
        container.innerHTML = `
            <div class="empty-archive">
                <h3>NO MATCHES FOUND</h3>
                <p>Try adjusting your search or browse all newsletters</p>
            </div>
        `;
        return;
    }

    // Group newsletters by year
    const years = {};
    displayedNewsletters.forEach(newsletter => {
        const year = newsletter.date.split('-')[0];
        if (!years[year]) years[year] = [];
        years[year].push(newsletter);
    });

    let html = '';
    Object.keys(years).sort((a, b) => b - a).forEach(year => {
        html += `
            <div class="year-section">
                <div class="year-label">${year}</div>
                <div class="newsletter-list">
        `;
        years[year].forEach(newsletter => {
            html += createNewsletterItem(newsletter);
        });
        html += '</div></div>';
    });

    container.innerHTML = html;

    // Click handler
    container.querySelectorAll('.newsletter-item').forEach(item => {
        item.addEventListener('click', () => {
            window.location.href = item.dataset.path;
        });
    });
}

function createNewsletterItem(newsletter) {
    const parts = newsletter.title.split(':');
    const mainTitle = parts[0].trim();
    const subtitle = parts[1] ? parts[1].trim() : '';

    return `
        <div class="newsletter-item" data-path="${newsletter.path}">
            <div class="newsletter-number">#${newsletter.issue}</div>
            <div class="newsletter-content">
                <div class="newsletter-title">${mainTitle}</div>
                <div class="newsletter-meta">
                    ${formatDate(newsletter.date)}
                    ${subtitle ? ` • ${subtitle}` : ''}
                </div>
            </div>
            <div class="newsletter-arrow">→</div>
        </div>
    `;
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                    'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

function updateCount() {
    const countElement = document.getElementById('result-count');
    if (!countElement) return;
    const total = allNewsletters.length;
    const showing = displayedNewsletters.length;

    countElement.textContent = 
        showing === total
            ? `${total} ${total === 1 ? 'ISSUE' : 'ISSUES'}`
            : `${showing} OF ${total}`;
}

function showError() {
    const container = document.getElementById('newsletter-list');
    if (container) {
        container.innerHTML = `
            <div class="empty-archive">
                <h3>UNABLE TO LOAD ARCHIVE</h3>
                <p>Please refresh the page or try again later</p>
            </div>
        `;
    }
    const countElement = document.getElementById('result-count');
    if (countElement) {
        countElement.textContent = 'ERROR';
    }
}
