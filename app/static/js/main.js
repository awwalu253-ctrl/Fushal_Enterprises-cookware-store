// Global functions and initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Sticky header
    const header = document.querySelector('.sticky-header');
    if (header) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 100) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }
    
    // Scroll to top button
    const scrollBtn = document.createElement('div');
    scrollBtn.className = 'scroll-top';
    scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    document.body.appendChild(scrollBtn);
    
    scrollBtn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 500) {
            scrollBtn.classList.add('show');
        } else {
            scrollBtn.classList.remove('show');
        }
    });
    
    // Auto-dismiss flash messages
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            setTimeout(() => bsAlert.close(), 5000);
        });
    }, 3000);
    
    // Product image zoom on hover
    document.querySelectorAll('.product-image').forEach(image => {
        const img = image.querySelector('img');
        if (img) {
            image.addEventListener('mousemove', function(e) {
                const rect = this.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width * 100;
                const y = (e.clientY - rect.top) / rect.height * 100;
                img.style.transformOrigin = `${x}% ${y}%`;
                img.style.transform = 'scale(1.2)';
            });
            
            image.addEventListener('mouseleave', function() {
                img.style.transform = 'scale(1)';
            });
        }
    });
});

// Search Autocomplete functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const suggestionsDiv = document.getElementById('searchSuggestions');
    
    if (!searchInput) return;
    
    let debounceTimer;
    let currentRequest = null;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            suggestionsDiv.classList.remove('show');
            return;
        }
        
        debounceTimer = setTimeout(() => {
            // Cancel previous request if exists
            if (currentRequest) {
                currentRequest.abort();
            }
            
            // Create new abort controller
            const controller = new AbortController();
            currentRequest = controller;
            
            fetch(`/search/suggest?q=${encodeURIComponent(query)}`, {
                signal: controller.signal
            })
            .then(response => response.json())
            .then(data => {
                if (data.length > 0) {
                    displaySuggestions(data);
                    suggestionsDiv.classList.add('show');
                } else {
                    suggestionsDiv.classList.remove('show');
                }
            })
            .catch(error => {
                if (error.name !== 'AbortError') {
                    console.error('Search error:', error);
                }
            });
        }, 300);
    });
    
    function displaySuggestions(suggestions) {
        if (!suggestionsDiv) return;
        
        suggestionsDiv.innerHTML = suggestions.map(item => {
            if (item.type === 'product') {
                return `
                    <a href="${item.url}" class="suggestion-item">
                        <img src="${item.image || '/static/images/placeholder.jpg'}" alt="${item.name}">
                        <div class="suggestion-info">
                            <div class="suggestion-name">${escapeHtml(item.name)}</div>
                            <div class="suggestion-price">₦${parseFloat(item.price).toLocaleString()}</div>
                        </div>
                        <span class="suggestion-type">Product</span>
                    </a>
                `;
            } else if (item.type === 'category') {
                return `
                    <a href="${item.url}" class="suggestion-item">
                        <div class="suggestion-info">
                            <div class="suggestion-name">${escapeHtml(item.name)}</div>
                            <div class="suggestion-category">Browse all ${item.name}</div>
                        </div>
                        <span class="suggestion-type">Category</span>
                    </a>
                `;
            }
            return '';
        }).join('');
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
            suggestionsDiv.classList.remove('show');
        }
    });
    
    // Handle keyboard navigation
    let selectedIndex = -1;
    
    searchInput.addEventListener('keydown', function(e) {
        const items = document.querySelectorAll('.suggestion-item');
        if (items.length === 0) return;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            highlightSuggestion(items, selectedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            highlightSuggestion(items, selectedIndex);
        } else if (e.key === 'Enter' && selectedIndex >= 0) {
            e.preventDefault();
            items[selectedIndex].click();
        }
    });
    
    function highlightSuggestion(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.style.background = '#f0f0f0';
            } else {
                item.style.background = '';
            }
        });
    }
});

// Password strength indicator
function checkPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.match(/[A-Z]/)) strength++;
    if (password.match(/[a-z]/)) strength++;
    if (password.match(/[0-9]/)) strength++;
    if (password.match(/[^A-Za-z0-9]/)) strength++;
    
    const strengthMap = {
        0: { text: 'Very Weak', class: 'bg-danger', width: '20%' },
        1: { text: 'Weak', class: 'bg-danger', width: '40%' },
        2: { text: 'Fair', class: 'bg-warning', width: '60%' },
        3: { text: 'Good', class: 'bg-info', width: '80%' },
        4: { text: 'Strong', class: 'bg-success', width: '100%' },
        5: { text: 'Very Strong', class: 'bg-success', width: '100%' }
    };
    
    return strengthMap[strength] || strengthMap[0];
}

document.querySelectorAll('input[type="password"]').forEach(input => {
    input.addEventListener('input', function() {
        const container = this.parentElement.parentElement.querySelector('.password-strength');
        if (!container) return;
        
        const strength = checkPasswordStrength(this.value);
        container.innerHTML = `
            <div class="progress mt-2" style="height: 5px;">
                <div class="progress-bar ${strength.class}" style="width: ${strength.width}"></div>
            </div>
            <small class="text-muted">${strength.text}</small>
        `;
    });
});

// Lazy loading images
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            observer.unobserve(img);
        }
    });
});

document.querySelectorAll('img[data-src]').forEach(img => {
    imageObserver.observe(img);
});

// Add to cart with loading state
window.addToCart = function(productId, quantity = 1) {
    const button = event?.currentTarget;
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    
    fetch('/cart/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ product_id: productId, quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Added to cart!', 'success');
            updateCartCount(data.cart_count);
            
            // Animate cart icon
            const cartIcon = document.querySelector('.cart-icon');
            if (cartIcon) {
                cartIcon.classList.add('bounce');
                setTimeout(() => cartIcon.classList.remove('bounce'), 500);
            }
        } else {
            showToast(data.error || 'Failed to add', 'error');
        }
    })
    .catch(() => showToast('Something went wrong', 'error'))
    .finally(() => {
        if (button) {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-shopping-cart"></i>';
        }
    });
};