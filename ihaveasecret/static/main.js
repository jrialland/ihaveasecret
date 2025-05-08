
//for every element with a x-clipboard-data attribute, add a click event listener
document.querySelectorAll('[x-clipboard-data]').forEach(item => {
    item.addEventListener('click', event => {
        let data = item.getAttribute('x-clipboard-data');
        navigator.clipboard.writeText(data).then(function() {
            console.log('Async: Copying to clipboard was successful!');
        }, function(err) {
            console.error('Async: Could not copy text: ', err);
        });
    });
});

//for every textarea with a x-maxlength attribute, add a keyup event listener
document.querySelectorAll('textarea[x-maxlength]').forEach(item => {
    
    // get the max length
    let maxLength = parseInt(item.getAttribute('x-maxlength'));
    
    // create a message zone to display the current length
    let messagezone = document.createElement('div');
    messagezone.classList.add('messagezone');
    item.parentNode.insertBefore(messagezone, item.nextSibling);
    
    // function to update the message
    let updateMessage = () => {
        let currentLength = item.value.length;
        if(currentLength > maxLength) {
            item.value = item.value.substring(0, maxLength);
            currentLength = maxLength;
        }
        item.value = item.value.substring(0, maxLength);
        messagezone.innerHTML = `<span class="tag"> ${currentLength == maxLength ? '⚠️' : ''} ${currentLength}/${maxLength} characters</span>`;
    }

    // update the message when the user types
    item.addEventListener('keyup', event => {
        updateMessage();
    });

    // and also update the message when the page loads
    updateMessage();

});

//for every password input have autocomplete="new-password", add a keyup event listener that checks if the password is strong enough
document.querySelectorAll('input[type="password"][autocomplete="new-password"]').forEach(item => {
    
    // create a message zone to display the current strength
    let messagezone = document.createElement('div');
    messagezone.classList.add('messagezone');
    item.parentNode.insertBefore(messagezone, item.nextSibling);
    
    // function to update the message
    let updateMessage = () => {
        if (item.value.length === 0) {
            messagezone.innerHTML = '';
            return;
        }
        let s = zxcvbn(item.value).score;
        let strengthText = ['⚠️Very weak', '🤦Weak', '😑Reasonable', '👍Strong', '🕵️Very strong'][s];
        let tagClass = ['black', 'danger', 'warning', 'success', 'success'][s];
        messagezone.innerHTML = `<span class="tag is-${tagClass}">${s>3?'<strong>':''}${strengthText}${s>3?'</strong>':''}</span>`;
    }

    // update the message when the user types
    item.addEventListener('keyup', event => {
        updateMessage();
    });

    // and also update the message when the page loads
    updateMessage();

});