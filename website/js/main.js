(function () {
  const menuButton = document.querySelector('.menu-btn');
  const nav = document.querySelector('.nav');

  menuButton?.addEventListener('click', () => {
    const open = nav?.classList.toggle('open') || false;
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  });

  document.querySelectorAll('.nav a').forEach((link) => {
    link.addEventListener('click', () => {
      nav?.classList.remove('open');
      menuButton?.setAttribute('aria-expanded', 'false');
      menuButton?.setAttribute('aria-label', 'Open menu');
    });
  });

  async function copyText(text, button) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      textarea.remove();
    }
    const original = button.textContent;
    button.textContent = 'Copied';
    setTimeout(() => { button.textContent = original; }, 2000);
  }

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = document.querySelector(button.dataset.copy);
      if (target) copyText(target.textContent.trim(), button);
    });
  });

  function activateTab(tab, moveFocus = false) {
    const codeWindow = tab.closest('.code-window');
    const id = tab.dataset.tab;
    codeWindow.querySelectorAll('.code-tab').forEach((item) => {
      const selected = item === tab;
      item.classList.toggle('active', selected);
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
    });
    codeWindow.querySelectorAll('.code-panel').forEach((panel) => {
      const selected = panel.id === id;
      panel.classList.toggle('active', selected);
      panel.hidden = !selected;
    });
    if (moveFocus) tab.focus();
  }

  document.querySelectorAll('.code-tab').forEach((tab, index, tabs) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', (event) => {
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = tabs.length - 1;
      else return;
      event.preventDefault();
      activateTab(tabs[next], true);
    });
  });

  const reveals = document.querySelectorAll('.reveal');
  if (reveals.length && 'IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    reveals.forEach((element) => observer.observe(element));
  } else {
    reveals.forEach((element) => element.classList.add('visible'));
  }

  const demoInput = document.getElementById('memory-demo-input');
  const demoResponse = document.getElementById('memory-demo-response');
  const demoSubmit = document.getElementById('memory-demo-submit');
  const demoSuggestions = document.querySelectorAll('.demo-suggestion');
  const demoResponses = {
    'How do I fix ModuleNotFoundError?':
      'Example answer: check which Python environment you are using, activate your virtualenv, and run pip list to verify the package is installed.',
    'Search my past conversations about Python':
      'Example result: three similar messages about Python environments and package installation. A real run would search only the session user’s messages.',
    'Store that my favorite language is Python':
      'Example result: key=fav_language, value=Python for user alice would be stored in memories.json. This demo does not write data.',
    default:
      'In a real setup, neuDB would embed the query, call messages.search_similar("embedding", vector), and fall back to search_text when embeddings are unavailable.'
  };

  function runDemo(query) {
    const value = query.trim();
    if (!value || !demoResponse || !demoInput) return;
    demoInput.value = value;
    demoResponse.hidden = false;
    demoResponse.classList.remove('visible');
    demoResponse.className = 'demo-response';
    const thinking = document.createElement('span');
    thinking.className = 'demo-thinking';
    thinking.textContent = 'Preparing a simulated example…';
    demoResponse.replaceChildren(thinking);
    requestAnimationFrame(() => demoResponse.classList.add('visible'));

    setTimeout(() => {
      const answer = document.createElement('p');
      answer.className = 'demo-answer';
      answer.textContent = demoResponses[value] || demoResponses.default;
      demoResponse.replaceChildren(answer);

      const memoryCard = document.getElementById('card-memory');
      const prompt = memoryCard?.querySelector('.mock-prompt strong');
      const response = memoryCard?.querySelector('.mock-response');
      if (prompt) prompt.textContent = value;
      if (response) response.textContent = answer.textContent;
    }, 450);
  }

  demoSubmit?.addEventListener('click', () => runDemo(demoInput?.value || ''));
  demoInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runDemo(demoInput.value);
    }
  });
  demoSuggestions.forEach((chip) => {
    chip.addEventListener('click', () => runDemo(chip.dataset.query || chip.textContent));
  });

  const productNav = document.getElementById('product-nav');
  const productLinks = [...document.querySelectorAll('.product-nav-link')];
  const productCards = [...document.querySelectorAll('[data-product-card]')];
  const showcase = document.getElementById('showcase');

  function updateProductNav() {
    if (!productNav || !showcase) return;
    const bounds = showcase.getBoundingClientRect();
    const headerHeight = 72;
    productNav.classList.toggle('is-visible', bounds.top < headerHeight + 120 && bounds.bottom > headerHeight + 120);

    let activeId = productCards[0]?.id;
    productCards.forEach((card) => {
      if (card.getBoundingClientRect().top < window.innerHeight * 0.55) activeId = card.id;
    });
    productLinks.forEach((link) => {
      const active = link.getAttribute('href') === `#${activeId}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    });
  }

  window.addEventListener('scroll', updateProductNav, { passive: true });
  window.addEventListener('resize', updateProductNav);
  updateProductNav();
})();