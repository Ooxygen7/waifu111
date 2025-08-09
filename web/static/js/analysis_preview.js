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
});