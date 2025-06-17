document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signupForm');
    const loginForm = document.getElementById('loginForm');
    const messageDiv = document.getElementById('message');

    const API_BASE_URL = 'http://127.0.0.1:5000/api';

    const displayMessage = (message, isError = false) => {
        if (messageDiv) {
            messageDiv.textContent = message;
            messageDiv.className = isError ? 'text-red-500 text-sm' : 'text-green-500 text-sm';
            messageDiv.classList.add('mt-4', 'text-center');
        }
    };

    const validateEmail = (email) => {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(String(email).toLowerCase());
    };

    if (signupForm) {
        signupForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            displayMessage(''); // Clear previous messages

            const email = signupForm.email.value.trim();
            const password = signupForm.password.value.trim();
            const referred_by_user_id_input = signupForm.referred_by_user_id;
            let referred_by_user_id = referred_by_user_id_input ? referred_by_user_id_input.value.trim() : null;


            if (!email || !password) {
                displayMessage('Email and password are required.', true);
                return;
            }
            if (!validateEmail(email)) {
                displayMessage('Invalid email format.', true);
                return;
            }
            if (password.length < 6) { // Basic password length validation
                displayMessage('Password must be at least 6 characters long.', true);
                return;
            }

            const payload = { email, password };
            if (referred_by_user_id) {
                payload.referred_by_user_id = parseInt(referred_by_user_id, 10);
                 if (isNaN(payload.referred_by_user_id)) {
                    displayMessage('Referred by User ID must be a number.', true);
                    return;
                }
            }


            try {
                const response = await fetch(`${API_BASE_URL}/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                const data = await response.json();

                if (response.ok) {
                    displayMessage(data.message || 'Registration successful!');
                    signupForm.reset();
                } else {
                    displayMessage(data.error || 'Registration failed.', true);
                }
            } catch (error) {
                console.error('Registration error:', error);
                displayMessage('An error occurred during registration. Please try again.', true);
            }
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            displayMessage(''); // Clear previous messages

            const email = loginForm.email.value.trim();
            const password = loginForm.password.value.trim();

            if (!email || !password) {
                displayMessage('Email and password are required.', true);
                return;
            }
            if (!validateEmail(email)) {
                displayMessage('Invalid email format.', true);
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, password }),
                });

                const data = await response.json();

                if (response.ok) {
                    displayMessage(data.message || 'Login successful!');
                    // In a real app, you'd redirect or update UI for logged-in state
                    loginForm.reset();
                } else {
                    displayMessage(data.error || 'Login failed. Please check your credentials.', true);
                }
            } catch (error) {
                console.error('Login error:', error);
                displayMessage('An error occurred during login. Please try again.', true);
            }
        });
    }
});
