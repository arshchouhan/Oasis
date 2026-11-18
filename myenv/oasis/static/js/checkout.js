(() => {
  const form = document.getElementById('checkoutForm');
  const button = document.getElementById('openPayment');
  if (!form || !button) return;

  button.addEventListener('click', async () => {
    if (!form.reportValidity()) return;
    button.disabled = true;
    button.textContent = 'Opening secure checkout…';
    const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
    try {
      const response = await fetch(form.dataset.orderUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrf, Accept: 'application/json' },
        credentials: 'same-origin'
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to start checkout.');
      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        name: 'Oasis',
        description: 'Eye-care marketplace order',
        order_id: data.order_id,
        prefill: { name: form.elements.full_name.value },
        theme: { color: '#008c9b' },
        handler(payment) {
          Object.entries(payment).forEach(([name, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            input.value = value;
            form.appendChild(input);
          });
          form.submit();
        },
        modal: { ondismiss: () => { button.disabled = false; button.textContent = 'Continue to payment'; } }
      };
      new window.Razorpay(options).open();
    } catch (error) {
      window.alert(error.message);
      button.disabled = false;
      button.textContent = 'Continue to payment';
    }
  });
})();
