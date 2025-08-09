document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('analysis-modal');
    const modalImage = document.getElementById('modal-image');
    const modalText = document.getElementById('modal-text');
    const modalUser = document.getElementById('modal-user');
    const modalTime = document.getElementById('modal-time');
    const closeButton = modal.querySelector('.modal-close');
    const analysisCards = document.querySelectorAll('.analysis-card');

    function openModal(card) {
        const imageUrl = card.dataset.imageUrl;
        const content = card.dataset.content;
        const user = card.dataset.user;
        const time = card.dataset.time;

        modalImage.src = imageUrl;
        modalText.textContent = content;
        modalUser.textContent = user;
        modalTime.textContent = time;
        
        modal.classList.add('show');
        modal.style.pointerEvents = 'auto';
    }

    function closeModal() {
        modal.classList.remove('show');
        modal.style.pointerEvents = 'none';
    }

    analysisCards.forEach(card => {
        card.addEventListener('click', () => openModal(card));
    });

    closeButton.addEventListener('click', closeModal);

    modal.addEventListener('click', function (event) {
        // Close if clicked on the overlay, but not on the container itself
        if (event.target === modal) {
            closeModal();
        }
    });

    window.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });

    let page = 1;
    let isLoading = false;
    let hasNext = true;
    const loadingIndicator = document.getElementById('loading-indicator');
    const grid = document.querySelector('.analysis-grid');

    function loadMoreItems() {
        if (isLoading || !hasNext) return;

        isLoading = true;
        loadingIndicator.style.display = 'block';
        page++;

        fetch(`/api/analysis_previews?page=${page}`)
            .then(response => response.json())
            .then(data => {
                data.items.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'analysis-card';
                    card.dataset.imageUrl = item.image_url;
                    card.dataset.content = item.content;
                    card.dataset.user = item.user_name;
                    card.dataset.time = item.date_time;

                    card.innerHTML = `
                        <div class="analysis-image-wrapper">
                            <img src="${item.image_url}" alt="分析图片" loading="lazy">
                        </div>
                        <div class="analysis-content">
                            <pre>${item.content}</pre>
                        </div>
                        <div class="analysis-footer">
                            <span>${item.user_name}</span> | <span>${item.date_time}</span>
                        </div>
                    `;
                    grid.appendChild(card);
                    card.addEventListener('click', () => openModal(card));
                });

                hasNext = data.has_next;
                isLoading = false;
                loadingIndicator.style.display = 'none';
            })
            .catch(error => {
                console.error('Error loading more items:', error);
                isLoading = false;
                loadingIndicator.style.display = 'none';
            });
    }

    window.addEventListener('scroll', () => {
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
            loadMoreItems();
        }
    });
});