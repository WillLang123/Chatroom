let currentUserID = null;
let currentUsername = null;
let messageStreams = {};
let DBMutex = new Set();

//hyphen
function toggleForm(formType){
    const loginForm = document.getElementById("loginPage");
    const registerForm = document.getElementById("registerPage");
    if(Object.is(formType,"login")){
        loginForm.style.display = "block";
        registerForm.style.display = "none";
    } else {
        loginForm.style.display = "none";
        registerForm.style.display = "block";
    }
}

async function register(){
    const username = document.getElementById("registerUser").value;
    const password = document.getElementById("registerPW").value;
    try{
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            await login(username, password);
        } else {
            document.getElementById("registerError").textContent = dataFromServer.problem;
        }
    } catch(error){
        document.getElementById("registerError").textContent = "A problem occurred during registration";
    }
}

async function login(username=null, password=null){
    if((Object.is(username,null)) || (Object.is(password,null))){
        username = document.getElementById("loginUser").value;
        password = document.getElementById("loginPW").value;
    }
    try{
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            document.getElementById("regLoginDisplay").style.display = "none";
            document.getElementById("chatroomsDisplay").style.display = "block";
            currentUserID = dataFromServer.user.id;
            currentUsername = dataFromServer.user.username;
            await loadChatrooms();
        } else {
            document.getElementById("loginError").textContent = dataFromServer.problem;
        }
    } catch(error){
        document.getElementById("loginError").textContent = "A problem occurred during login";
    }
}

async function logout(){
    try{
        const response = await fetch("/logout", { method: "POST" });
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            document.getElementById("regLoginDisplay").style.display = "block";
            document.getElementById("chatroomsDisplay").style.display = "none";
            currentUserID = null;
            currentUsername = null;
            document.getElementById("loginUser").value = "";
            document.getElementById("loginPW").value = "";
            document.getElementById("registerUser").value = "";
            document.getElementById("registerPW").value = "";
            document.getElementById("loginError").textContent = "";
            document.getElementById("registerError").textContent = "";
            Object.values(messageStreams).forEach(stream => stream.close());
            messageStreams = {};
        }
    } catch(error){
        console.error("Problem during logout:", error);
    }
}

async function checkLogin(){
    try{
        const response = await fetch("/checkLogin");
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok") && dataFromServer.authenticated){
            document.getElementById("regLoginDisplay").style.display = "none";
            document.getElementById("chatroomsDisplay").style.display = "block";
            currentUserID = dataFromServer.user.id;
            currentUsername = dataFromServer.user.username;
            await loadChatrooms();
        }
    } catch(error){
        console.error("Problem checking authentication:", error);
    }
}

async function createChatroom(){
    const name = document.getElementById("chatroomName").value;
    if(!name){
        return;
    } 
    try{
        const response = await fetch("/createChatroom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
        });
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            document.getElementById("chatroomName").value = "";
            await loadChatrooms();
        } else {
            alert(dataFromServer.message);
        }
    } catch(error){
        console.error("Problem creating chatroom:", error);
        alert("Failed to create chatroom. Please try again.");
    }
}

async function joinChatroom(){
    const id = document.getElementById("chatroomID").value;
    if((Object.is(id,null))){
        return;
    }
    try{
        const response = await fetch("/joinChatroom", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chatroomID: parseInt(id) })
        });
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            document.getElementById("chatroomID").value = "";
            await loadChatrooms();
        } else {
            alert(dataFromServer.message);
        }
    } catch(error){
        console.error("Problem joining chatroom:", error);
        alert("Failed to join chatroom. Please try again.");
    }
}

async function deleteChatroom(chatroomID){
    // Check if chatroom is already being deleted
    if(DBMutex.has(chatroomID)){
        return;
    }
    //Creates confirm option before it does so
    if(!confirm("Confirm deleting this chatroom")){
        return;
    }
    try{
        //add chatroomID in TODO delete list
        DBMutex.add(chatroomID);
        //Close the message stream about it and delete it
        if(messageStreams[chatroomID]){
            messageStreams[chatroomID].close();
            delete messageStreams[chatroomID];
        }
        //disables delete button for that specific chatroom tab
        const deleteAdminButton = document.querySelector(`#chatroomTabs .tab[chatroomID="${chatroomID}"] .buttonDelete`);
        if(deleteAdminButton){
            deleteAdminButton.disabled = true;
        }
        //Calls server using curl to delete that chatroom
        const response = await fetch(`/deleteChatroom/${chatroomID}`, { method: "DELETE" });
        const dataFromServer = await response.json();
        //figures out if it worked
        if(Object.is(dataFromServer.signal,"ok")){
            const tab = document.querySelector(`.tab[chatroomID="${chatroomID}"]`);
            const chatroomArea = document.getElementById(`chatroomID${chatroomID}`);
            //removes elements about that chatroom
            if(tab){
                //it begins to make tabs for next or previous chatroom to become its next and previous tabs
                //  for the chatroom that got deleted
                if(tab.classList.contains("active")){
                    const nextTab = tab.nextElementSibling || tab.previousElementSibling;
                    if(nextTab){
                        const nextChatroomID = nextTab.getAttribute("chatroomID");
                        switchTab(nextChatroomID);
                    }
                }
                tab.remove();
            }
            //deletes tabs and chatroomArea about that chatroom and shows home page if there are no more tabs left
            if(chatroomArea){
                chatroomArea.remove();
            } 
            const tabs = document.querySelectorAll(".tab");
            const HTMLBlock = `<div class="welcomeBanner">
                                    <h2>Welcome to the Chatroom Website</h2>
                                    <p>Either use an ID to join or create a chatroom to get started.</p>
                                </div>`
            if(Object.is(tabs.length,0)){
                document.getElementById("tabContent").innerHTML = HTMLBlock;
            }
        } else {
            alert(dataFromServer.message || "Failed to delete chatroom");
        }
    } catch(error){
        //shows error if there was a problem
        console.error("Problem deleting chatroom:", error);
        alert("Failed to delete chatroom. Please try again.");
    } finally {
        //removes chatroom from delete list and makes delete button work again in that area
        DBMutex.delete(chatroomID);
        const deleteAdminButton = document.querySelector(`#chatroomTabs .tab[chatroomID="${chatroomID}"] .buttonDelete`);
        if(deleteAdminButton){
            deleteAdminButton.disabled = false;
        }
    }
}

async function leaveChatroom(chatroomID) {
    if (DBMutex.has(chatroomID)){
        return;
    }
    if (!confirm('Confirm leaving this chatroom?')) {
        return;
    }
    try {
        DBMutex.add(chatroomID);
        if (messageStreams[chatroomID]) {
            messageStreams[chatroomID].close();
            delete messageStreams[chatroomID];
        }
        const button = document.querySelector(`.buttonLeave[onclick="leaveChatroom(${chatroomID})"]`);
        if (button) {
            button.disabled = true;
        }
        const response = await fetch(`/leaveChatroom/${chatroomID}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        if (!data.problem) {
            const tab = document.querySelector(`.tab[chatroomID="${chatroomID}"]`);
            const chatroomArea = document.getElementById(`chatroomID${chatroomID}`);
            if (tab) {
                if (tab.classList.contains("active")) {
                    const nextTab = tab.nextElementSibling || tab.previousElementSibling;
                    if (nextTab) {
                        const nextChatroomID = nextTab.getAttribute("chatroomID");
                        switchTab(nextChatroomID);
                    }
                }
                tab.remove();
            }
            if (chatroomArea) {
                chatroomArea.remove();
            }
            const tabs = document.querySelectorAll(".tab");
            if (Object.is(tabs.length, 0)) {
                document.getElementById("tabContent").innerHTML = `<div class="welcomeBanner">
                    <h2>Welcome to the COSC 4360-01 chatroom website</h2>
                    <p>Either get a chatroom ID from someone else to join or just create a chatroom to message others.</p>
                </div>`;
            }
        } else {
            alert(data.problem);
        }
    } catch (error) {
        console.error('Error leaving chatroom:', error);
        alert('Failed to leave chatroom');
    } finally {
        DBMutex.delete(chatroomID);
        const button = document.querySelector(`.buttonLeave[onclick="leaveChatroom(${chatroomID})"]`);
        if (button) {
            button.disabled = false;
        }
    }
}

async function loadChatrooms(){
    try{
        const response = await fetch("/chatrooms");
        const dataFromServer = await response.json();
        const tabsContainer = document.getElementById("chatroomTabs");
        const contentContainer = document.getElementById("tabContent");
        if(!tabsContainer || !contentContainer){
            return;
        }
        tabsContainer.innerHTML = "";
        contentContainer.innerHTML = "";
        if(!dataFromServer.chatrooms || Object.is(dataFromServer.chatrooms.length, 0)){
            HTMLBlock = `<div class="welcomeBanner">
                            <h2>Welcome to the COSC 4360-01 chatroom website</h2>
                            <p>Either get a chatroom ID from someone else to join or just create a chatroom to message others.</p>
                        </div>`;
            contentContainer.innerHTML = HTMLBlock;
            return;
        }
        dataFromServer.chatrooms.forEach((chatroom, index) => {
            const tab = document.createElement("div");
            if(Object.is(index,0)){
                tab.className = "tab active";
            } else {
                tab.className = "tab";
            }
            tab.setAttribute("chatroomID", chatroom.id);
            tab.onclick = () => switchTab(chatroom.id);
            //Renders tab for each classroom with delete button and chatroom id for invites
            if(chatroom.isAdmin){
                HTMLBlock = `
                        <div class=deleteChatContainer">
                            <span style="font-size: 12px; color: #95a5a6;">(ID: ${chatroom.id})</span>
                            <button class="button buttonDelete" onclick="event.stopPropagation(); deleteChatroom(${chatroom.id})">
                                Delete
                            </button>
                        </div>`
            } else {
                HTMLBlock = `
                        <div class=deleteChatContainer">
                            <span style="font-size: 12px; color: #95a5a6;">(ID: ${chatroom.id})</span>
                            <button class="button buttonLeave" onclick="event.stopPropagation(); leaveChatroom(${chatroom.id})">
                                Leave
                            </button>
                        </div>`
            }
            tab.innerHTML = `<div class="tabContent" style="display: flex; align-items: center; gap: 10px;">
                                <span>${chatroom.name}</span>
                                ${HTMLBlock}
                            </div>`;
            tabsContainer.appendChild(tab);
            const chatroomArea = document.createElement("div");
            if(Object.is(index,0)){
                chatroomArea.className = "chatroomSection active";
            } else {    
                chatroomArea.className = "chatroomSection";
            }
            chatroomArea.id = `chatroomID${chatroom.id}`;
            chatroomArea.setAttribute("chatroomID", chatroom.id);
            //Renders HTML for sending messages
            HTMLBlock = ""
            if(chatroom.isAdmin){
                HTMLBlock = `<small>Chatroom ID: ${chatroom.id}</small>`
            } else {
                HTMLBlock = ""
            }
            chatroomArea.innerHTML = `
                <div class="chatroomBanner">
                    <h3>${chatroom.name}</h3>
                    ${HTMLBlock}
                </div>
                <div class="messages" id="messageTable${chatroom.id}"></div>
                <div class="messageBox">
                    <input type="text" placeholder="Put message here">
                    <button class="button buttonMain" onclick="sendMessage(${chatroom.id})">Send</button>
                </div>`;
            contentContainer.appendChild(chatroomArea);
            const input = chatroomArea.querySelector(".messageBox input");
            //takes input and looks for enter key or submit button and tries to send messsage with chatroom id
            input.addEventListener("keypress", (e) => {
                if(Object.is(e.key,"Enter")){
                    e.preventDefault();
                    sendMessage(chatroom.id);
                }
            });
            loadMessages(chatroom.id);
            setupMessageStream(chatroom.id);
        });
    } catch(error){
        console.error("Problem loading chatrooms:", error);
    }
}

function switchTab(chatroomID){
    document.querySelectorAll(".tab").forEach(tab => {
        if(tab.getAttribute("chatroomID") == chatroomID){
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });
    document.querySelectorAll(".chatroomSection").forEach(area => {
        if(area.getAttribute("chatroomID") == chatroomID){
            area.classList.add("active");
        } else {
            area.classList.remove("active");
        }
    });
}

async function loadMessages(chatroomID){
    try{
        const response = await fetch(`/chatroom/${chatroomID}/messages`);
        const dataFromServer = await response.json();
        if(Object.is(dataFromServer.signal,"ok")){
            const messageContainer = document.querySelector(`#messageTable${chatroomID}`);
            if(!messageContainer){
                return;
            }
            messageContainer.innerHTML = "";
            dataFromServer.messages.forEach(message => appendMessage(chatroomID, message));
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
    } catch(error){
        console.error("Problem loading messages:", error);
    }
}

async function sendMessage(chatroomID){
    const input = document.querySelector(`#chatroomID${chatroomID} .messageBox input`);
    const message = input.value.trim();
    //trims input from HTML
    if(!message){
        return;
    } 
    //breaks if input is empty
    try{
        //sends curl message to server to send message as well as a json of the message
        const response = await fetch(`/chatroom/${chatroomID}/send`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        const dataFromServer = await response.json();
        //waits for response and gives feedback accordingly
        if(Object.is(dataFromServer.signal,"ok")){
            input.value = "";
        } else {
            alert(dataFromServer.message);
        }
    } catch(error){
        console.error("Problem sending message:", error);
        alert("Failed to send message. Please try again.");
    }
}

function setupMessageStream(chatroomID){
    if(messageStreams[chatroomID]){
        messageStreams[chatroomID].close();
        delete messageStreams[chatroomID];
    }
    //reopens message stream if it is already opened
    const eventSource = new EventSource(`/chatroom/${chatroomID}/stream`);
    eventSource.onmessage = (event) => {
        try{
            const message = JSON.parse(event.data);
            if(message.error){
                return;
            }
            appendMessage(chatroomID, message);
        } catch(error){
            console.error("Problem processing message:", error);
        }
    };
    eventSource.onerror = (error) => {
        const chatroomArea = document.getElementById(`chatroomID${chatroomID}`);
        if(!chatroomArea){
            eventSource.close();
            delete messageStreams[chatroomID];
            return;
        }
        eventSource.close();
        delete messageStreams[chatroomID];
        setTimeout(() => {
            if(document.getElementById(`chatroomID${chatroomID}`)){
                setupMessageStream(chatroomID);
            }
        }, 5000);
    };
    messageStreams[chatroomID] = eventSource;
}

function appendMessage(chatroomID, message){
    const messageContainer = document.querySelector(`#messageTable${chatroomID}`);
    if(!messageContainer){
        return;
    }
    const existingMessage = messageContainer.querySelector(`[messageID="${message.id}"]`);
    if(existingMessage){
        return;
    }
    const messageElement = document.createElement("div");
    if(Object.is(message.userID,currentUserID)){
        messageElement.className = "message sent";
    } else {
        messageElement.className = "message received";
    }
    messageElement.setAttribute("messageID", message.id);
    const timestamp = new Date(message.timestamp).toLocaleTimeString();
    messageElement.innerHTML = `
        <div class="from">${message.username}</div>
        <div class="content">${cleanMessage(message.message)}</div>
        <div class="time">${timestamp}</div>
    `;
    messageContainer.appendChild(messageElement);
    const isNearBottom = messageContainer.scrollHeight - messageContainer.scrollTop - messageContainer.clientHeight < 100;
    if(isNearBottom){
        messageContainer.scrollTop = messageContainer.scrollHeight;
    }
}

function cleanMessage(unsafe){
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", checkLogin);