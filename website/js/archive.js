document.addEventListener('DOMContentLoaded', function() {
    // Fetch the newsletter metadata
    fetch('/newsletters.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load newsletter data');
            }
            return response.json();
        })
        .then(newsletters => {
            // Sort by date (newest first)
            newsletters.sort((a, b) => new Date(b.date) - new Date(a.date));
            
            // Display recent newsletters (top 10)
            const recentList = document.getElementById('recent-list');
            recentList.innerHTML = ''; // Clear loading message
            
            const recentNewsletters = newsletters.slice(0, 10);
            recentNewsletters.forEach(newsletter => {
                const item = document.createElement('li');
                item.className = 'newsletter-item';
                item.innerHTML = `
                    <span class="issue-number">#${newsletter.issue}</span>
                    <a href="${newsletter.path}">${newsletter.title}</a>
                    <span class="issue-date">${formatDate(newsletter.date)}</span>
                `;
                recentList.appendChild(item);
            });
            
            // Group by year and month for the archive
            const archiveSection = document.getElementById('archive-content');
            archiveSection.innerHTML = ''; // Clear loading message
            
            const newslettersByYear = groupByYear(newsletters);
            
            // Generate archive dropdowns
            Object.keys(newslettersByYear).sort().reverse().forEach(year => {
                const yearDetails = document.createElement('details');
                yearDetails.className = 'archive-year';
                
                const yearSummary = document.createElement('summary');
                yearSummary.textContent = year;
                yearDetails.appendChild(yearSummary);
                
                const newslettersByMonth = groupByMonth(newslettersByYear[year]);
                
                Object.keys(newslettersByMonth).sort().reverse().forEach(month => {
                    const monthDetails = document.createElement('details');
                    monthDetails.className = 'archive-month';
                    
                    const monthSummary = document.createElement('summary');
                    monthSummary.textContent = `${getMonthName(month)} (${newslettersByMonth[month].length} issues)`;
                    monthDetails.appendChild(monthSummary);
                    
                    const monthList = document.createElement('ul');
                    
                    newslettersByMonth[month].forEach(newsletter => {
                        const item = document.createElement('li');
                        item.innerHTML = `
                            <a href="${newsletter.path}">#${newsletter.issue}: ${formatDate(newsletter.date)} - ${newsletter.title}</a>
                        `;
                        monthList.appendChild(item);
                    });
                    
                    monthDetails.appendChild(monthList);
                    yearDetails.appendChild(monthDetails);
                });
                
                archiveSection.appendChild(yearDetails);
            });
        })
        .catch(error => {
            console.error('Error loading newsletters:', error);
            document.getElementById('recent-list').innerHTML = '<li class="newsletter-item">Failed to load recent newsletters. Please try again later.</li>';
            document.getElementById('archive-content').innerHTML = '<p>Failed to load archive. Please try again later.</p>';
        });
});

// Helper functions
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

function getMonthName(month) {
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                        'July', 'August', 'September', 'October', 'November', 'December'];
    return monthNames[parseInt(month) - 1];
}

function groupByYear(newsletters) {
    return newsletters.reduce((acc, newsletter) => {
        const year = newsletter.date.split('-')[0];
        if (!acc[year]) acc[year] = [];
        acc[year].push(newsletter);
        return acc;
    }, {});
}

function groupByMonth(newsletters) {
    return newsletters.reduce((acc, newsletter) => {
        const month = newsletter.date.split('-')[1];
        if (!acc[month]) acc[month] = [];
        acc[month].push(newsletter);
        return acc;
    }, {});
}
