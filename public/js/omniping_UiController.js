
var interval;

const client = new ApiClient();

const UICtrl = (function(client){
  // ========================================================= Internal Variables

  const domSelectors = {
    messageTd: "td#message",
    pollStatImg: "img#poll_img_pic",
    serverStatImg: "img#server_img_pic",
    bannerHeading: "div#banner span#opheading",
    bannerVer: "div#banner span#opver",
    banner: "div#banner",
    body: "body",
    startStopBtn: "button#start-stop",
    editTestsBtn: "button#e-tests",
    viewReportBtn: "button#v-report",
    mainDisplay: "div#main",
    modal: "div#modal",
    modalContent: "div#modal-content",
    curtain: "div#curtain",
    setupInfo: "div#setup-info",
    views: 'button.view-btn'
  };

  let narrowTableRows = false;
  let autoRefreshInterval = 3000; 

  // ========================================================= Internal Methods:

  const startUI = () => {
    updateMessage('checking Server...');
    client.get("/omniping/version")
      .then((data) => {
        showScreen(false);
        const bannerVer = document.querySelector(domSelectors.bannerVer);
        bannerVer.innerHTML = data.version;
        updateBanner(data);
        initialiseButtons(data.running);
        updateMessage(data.message);
        if (data.running == true){
          setPollingIndicator('on');
          getNewReport();
        }else if (data.running == false){
          setPollingIndicator('off');
          editTests();
        }else if (data.running === undefined){
          setPollingIndicator('err');
        }
      }).catch((err) => {
        showScreen(true);
        updateMessage(`${err.message}`);
        setPollingIndicator('err');
      });
  }

  // ========================================================= Initialise Buttons

  const initialiseButtons = (running) => {
    initStartStopBtn(running);
    const viewReportBtn = document.querySelector(domSelectors.viewReportBtn);
    viewReportBtn.addEventListener("click", getNewReport);
    const editTestsBtn = document.querySelector(domSelectors.editTestsBtn);
    editTestsBtn.addEventListener("click", editTests);
  }

  const initStartStopBtn = (running) => {
    const startStopBtn = document.querySelector(domSelectors.startStopBtn);
    startStopBtn.removeEventListener("click", toggleRun);
    startStopBtn.addEventListener("click", toggleRun);
    startStopBtn.classList = "button-primary";
    startStopText = "Start Polling";
    if (running == true){
      startStopText = "Stop Polling";
      startStopBtn.classList = "running";
    }
    startStopBtn.innerHTML = startStopText;
  }

  // ===================================================== Button Event Functions
  // ===================================================== Button Event Functions (nav)

  const toggleRun = (e) => {
    if (e.target.className == 'button-primary'){
      payload = {'action': 'start'};
    }else{
      payload = {'action': 'stop'};
    }
    sendStartStopReq(payload);
    e.preventDefault();
  }

  const sendStartStopReq = (payload) => {
    client.post("/omniping/engine", payload)
      .then((data) => {
        updateMessage(data.message);
        updatePolStat(data.polling);
      }).catch((err) => {
        if (err.message){
          updateMessage(`${err.message}`);
          setPollingIndicator("err");
        }
        return false
      });
  }
  
  const getNewReport = () => {
    client.get("/omniping/run")
      .then((data) => {
        updateReport(data);
      }).catch((err) => {
        updateMessage(`${err.message}`);
      });
  }
  
  const editTests = (e) => {
    client.get("/omniping/tests")
      .then((data) => {
        updateSetup(data);
      }).catch((err) => {
        updateMessage(`${err.message}`);
      });
  }

  // ===================================================== Button Event Functions (report)

  const clearReport = (e) => {
    payload = {'action': 'clear'};
    client.post("/omniping/engine", payload)
      .then((data) => {
        updateMessage(data.message);
        let restartAuto = false
        if (interval){
          stopAutoReport();
          restartAuto = true;
        }
        setTimeout( getNewReport, 1000);
        if (restartAuto){
          startAutoReport();
        }
      }).catch((err) => {
        if (err.message){
          updateMessage(`${err.message}`);
          setPollingIndicator("err");
        }
        return false;
      });
    e.preventDefault();   
  }

  const startAutoReport = (e) => {
    interval = setInterval(getNewReport, autoRefreshInterval);
    getNewReport();
    if (e !== undefined){
      e.preventDefault();   
    }
  }

  const stopAutoReport = (e) => {
    interval = clearInterval(interval);
    if (e !== undefined){
      getNewReport();
      e.preventDefault();   
    }
  }

  const toggleNarrowLines = (e) => {
    if (e.target.value == '-'){
      narrowTableRows = true;
    }else{
      narrowTableRows = false;
    }
    getNewReport();
  }

  // ===================================================== Button Event Functions (setup)

  const restartCp = (e) => {
    payload = {'action': 'restart_cp'};
    client.post("/omniping/engine", payload)
      .then((data) => {
        showScreen(true);
        setTimeout( startUI, 3000);

      }).catch((err) => {
        updateMessage(`${err.message}`);
        setServerIndicator('err');
      });
    e.preventDefault();   
  }

  const stopResetReport = (e) => {
    payload = {'action': 'reset'};
    client.post("/omniping/engine", payload)
      .then((data) => {
        updateMessage(data.message);
        updatePolStat(data.polling);
      }).catch((err) => {
        updateMessage(`${err.message}`);
        setServerIndicator('err');
      });
    e.preventDefault();   
  }

  const uploadConfig = (e) => {
    const payload = getSetupPayload();
    updateMessage(`sending new config: ${payload.tests.length} tests`);
    client.post("/omniping/setup", payload)
      .then((data) => {
        updateSetup(data);
      }).catch((err) => {
        updateMessage(`${err.message}`);
        setServerIndicator('err');
      });
    e.preventDefault();   
  }

  const viewConfigFile = (e) => {
    updateMessage('Fetching Data ...');
    client.get("/omniping/tests")
      .then((data) => {
        updateMessage('Fetched Setup File');
        delete data['content'];
        delete data['message'];
        const testFileStr = JSON.stringify(data, null, 2);
        const fileDiv = document.createElement('div');
        fileDiv.appendChild(document.createElement('hr'));
        const heading = document.createElement('h3');
        heading.appendChild(document.createTextNode('Stored Config:'));
        fileDiv.appendChild(heading);
        fileDiv.appendChild(document.createElement('hr'));
        const newTextArea = document.createElement('textarea');
        newTextArea.id = 'config-file';
        newTextArea.value = testFileStr;
        newTextArea.readOnly = true;
        newTextArea.classList = 'u-full-width';
        const newCol2 = document.createElement('div');
        newCol2.classList = 'twelve columns';
        newCol2.appendChild(newTextArea);
        const newRow = document.createElement('div');
        newRow.className = 'row';
        newRow.appendChild(newCol2);
        fileDiv.appendChild(newRow);
        fileDiv.appendChild(document.createElement('hr'));
        const copyBut = makeButton('Select All', selectAll, 'u-pull-left');
        fileDiv.appendChild(copyBut);
        showModal(fileDiv, doneFunc);
      }).catch((err) => {
        updateMessage(`Couldn't reach server ${err.message}`);
      });
    e.preventDefault();   
  }

  const selectAll = () => {
    var copyText = document.getElementById("config-file");
    copyText.select();
    copyText.setSelectionRange(0, 99999);
  }
  // ======================================================= GUI Update Functions

  const updateReport = (data) => {
    updateMessage(data.message);
    updatePolStat(data.running);
    colourViewBtns('v-report');
    const mainDisplay = document.querySelector(domSelectors.mainDisplay);
    reportPage = makeReport(data);
    mainDisplay.innerHTML = '';
    mainDisplay.appendChild(reportPage);
  }

  const updateSetup = (data) => {
    updateBanner(data);
    updateMessage(data.message);
    stopAutoReport();
    colourViewBtns('e-tests');
    const mainDisplay = document.querySelector(domSelectors.mainDisplay);
    mainDisplay.innerHTML = '';
    mainDisplay.appendChild(makeForm(data));
  }
  
  const updateBanner = (data) => {
    const bannerHeading = document.querySelector(domSelectors.bannerHeading);
    bannerHeading.innerHTML = data.heading;
    const banner = document.querySelector(domSelectors.banner);
    banner.style.background = data.colour;
    textColour = '#222222';
    if (goLight(data.colour)){
      textColour = '#DDDDDD';
    }
    banner.style.color = textColour;
  }

  const updatePolStat = (polling) => {
    initStartStopBtn(polling);
    let polInd = "off";
    if (polling){
      polInd = "on";
    }
    setPollingIndicator(polInd);      
  }
  
  const updateMessage = function(message, includeModal=false){
    messElem = document.querySelector(domSelectors.messageTd);
    messElem.textContent = `${message}`;
  }

  const colourViewBtns = (id) => {
    const views = document.querySelectorAll(domSelectors.views);
    views.forEach((btn) => {
      if (btn.id == id){
        btn.style.background = '#33bb334c';
      } else {
        btn.style.background = 'none';
      }
    });
  }

  const setServerIndicator = function(state="off"){
    const indicator = document.querySelector(domSelectors.serverStatImg);
    src = `/static/images/${state}.png`;
    indicator.src = src;
  }

  const setPollingIndicator = function(state="off"){
    const indicator = document.querySelector(domSelectors.pollStatImg);
    src = `/static/images/${state}.png`;
    indicator.src = src;
  }

  const showModal = (content, closeFunc=false) => {
    const modal = document.querySelector(domSelectors.modal);
    modalContent = document.querySelector(domSelectors.modalContent);
    modalContent.innerHTML = '';
    const newDiv = document.createElement('div');
    newDiv.className = 'modal-display';
    const closeBtn = document.createElement('button');
    closeBtn.classList = 'u-pull-right';
    closeBtn.appendChild(document.createTextNode('Close'));
    closeBtn.addEventListener('click', (e) => {
      modal.style.display = "none";
      closeFunc();
    });
    newDiv.appendChild(content);
    newDiv.appendChild(closeBtn);
    modalContent.appendChild(newDiv);
    modal.style.display = "block";
  }

  const showScreen = (show=false) => {
    const curtain = document.querySelector(domSelectors.curtain);
    
    if (show) {
      curtain.style.display = "block";
    }else{
      curtain.style.display = "none";
    }
  }

  const goLight = (hexColour) => {
    r = parseInt(hexColour.slice(1, 3), 16);
    g = parseInt(hexColour.slice(3, 5), 16);
    b = parseInt(hexColour.slice(5, 7), 16);
    if ((r + g + b) / 3 < 127){
      return true;
    }
    return false;
  }

  // ============================================================== Make Content (report)

  const makeReport = (data) => {
    const reportDiv = document.createElement('div');
    reportDiv.id = "report-info";
    reportDiv.appendChild(makeReportHead());
    reportDiv.appendChild(makeReportTable(data.tests));
    reportDiv.appendChild(makeReportFoot(data));
    return reportDiv;
  }

  const makeReportHead = () => {
    const reportHeadDiv = document.createElement('div');
    reportHeadDiv.classList = "u-full-width";
    const heading = document.createElement('h3');
    heading.appendChild(document.createTextNode('Report'));
    const refreshBtn = makeButton('Refresh', getNewReport, 'u-pull-right');
    let autoRefreshBtn = makeButton('Start Auto-Refresh', startAutoReport, 'u-pull-right button-primary');
    if (interval){
      autoRefreshBtn = makeButton('Stop Auto-Refresh', stopAutoReport, 'u-pull-right running');
    }
    autoRefreshBtn.id = 'auto-refresh';
    const resetBtn = makeButton('Clear Counters', clearReport, 'u-pull-right');
    let ntrVal = "-" 
    if (narrowTableRows){
      ntrVal = "+" 
    }
    const lineHeightButton = makeButton(`Row Height ${ntrVal}`, toggleNarrowLines, 'u-pull-right')
    lineHeightButton.value = ntrVal
    reportHeadDiv.appendChild(autoRefreshBtn);
    reportHeadDiv.appendChild(refreshBtn);
    reportHeadDiv.appendChild(resetBtn);
    reportHeadDiv.appendChild(lineHeightButton);
    reportHeadDiv.appendChild(heading);
    return reportHeadDiv;
  }
  
  const makeReportTable = (tests) => {
    const reportTabDiv = document.createElement('div');
    const repTab = document.createElement('table');
    repTab.id = "report-table"
    repTab.classList = 'u-full-width';
    const repTabHead = document.createElement('thead');
    const repTabHeadRow = document.createElement('tr');
    heads = ['Target', '', 'Result of Test', 'RTT', 'Performance', 'Time of Last Failure (Reason)'];
    heads.forEach((head, index) => {
      const repTabTh = document.createElement('th');
      repTabTh.appendChild(document.createTextNode(head));
      repTabHeadRow.appendChild(repTabTh);
    });
    repTabHead.appendChild(repTabHeadRow);
    repTab.appendChild(repTabHead);
    const repTabBody = document.createElement('tbody');
    tests.forEach((test) => {
      repTabBody.appendChild(makeReportTr(test));
    });
    repTab.appendChild(repTabBody);
    reportTabDiv.appendChild(repTab);
    return reportTabDiv;
  }

  const makeReportTr = (test) => {
    const tabRow = document.createElement('tr');
    let dontFlag = false
    if (test.status == '--'){
      tabRow.classList = '';
    }else if (test.status === 'Incomplete' && test.last_stat[0] !== 'G'){
      tabRow.classList = 'fail';
      dontFlag = true;
    }else if(test.status === 'Incomplete'){
      tabRow.classList = 'incomplete';
      dontFlag = true;
    }else if (!test.good){
      tabRow.classList = 'fail';
      dontFlag = true;
    }

    targetText = `${test.test}: ${test.host} - (${test.desc})`;
    tabRow.appendChild(makeTd(targetText));
    let src = "/static/images/failed.png";
    if (test.good){
      src = "/static/images/success.png";
    }
    tabRow.appendChild(makeTdImg(src));
    let flagStat = false;
    if (test.status[0] !== 'G' && !dontFlag){
      flagStat= true;
    }
    tabRow.appendChild(makeTd(test.status, flagStat));
    percText = `${test.total_successes} / ${test.total} (${test.success_percent})`;
    flag = false;
    if(test.total != test.total_successes && !dontFlag){
      flag = true;
    }
    tabRow.appendChild(makeTd(test.rtt));
    tabRow.appendChild(makeTd(percText, flag));
    lastFail = `${test.last_bad} (${test.last_bad_status})`;
    tabRow.appendChild(makeTd(lastFail, flag));
    return tabRow;
  }

  const makeTd = (value, flag) => {
    const td = document.createElement('td');
    if (flag){
      td.classList = "highlight";
    }
    if (narrowTableRows){
      td.classList = `${td.classList} narrow`
    }
    td.appendChild(document.createTextNode(value));
    return td;
  }

  const makeTdImg = (imgSrc) => {
    const td = document.createElement('td');
    if (narrowTableRows){
      td.classList = `${td.classList} narrow`
    }
    img = document.createElement('img');
    img.src = imgSrc;
    td.appendChild(img);
    return td;
  }

  const makeReportFoot = (data) => {
    const reportFootDiv = document.createElement('div');
    reportFootDiv.classList = "u-full-width";
    const heading = document.createElement('h5');
    heading.appendChild(document.createTextNode('Some Stats: '));
    const info = document.createElement('p');
    info.innerHTML = `Total Targets : ${data.tests.length}<br>
                      Started : ${data.started}<br>
                      Current Output : ${data.time}<br>
                      Number of polls : ${data.count}<br>
                      Duration (HH:MM:SS.nn) : ${data.duration}<br>`;
    reportFootDiv.appendChild(heading);
    reportFootDiv.appendChild(info);
    makeParagraphs(data.content, reportFootDiv)
    return reportFootDiv;
  }

  // ============================================================== Make Content (set up)

  const makeForm = (data) => {
    const formDiv = document.createElement('div');
    formDiv.id = 'setup-info';
    const tests = textifyTests(data, false);
    delete data['tests'];
    const content = data['content'];
    delete data['content'];
    updateMessage(data['message']);
    delete data['message'];
    const heading = document.createElement('h3');
    heading.appendChild(document.createTextNode('Set Up'));
    formDiv.appendChild(heading);
    formDiv.appendChild(document.createElement('hr'));
    formDiv.appendChild(makeButtons());
    formDiv.appendChild(document.createElement('hr'));
    for (var field in data){
      formDiv.appendChild(makeInput(field, data[field]));
    }
    formDiv.appendChild(makeTextArea(tests, 'settings-tests'));
    formDiv.appendChild(document.createElement('hr'));
    makeParagraphs(content, formDiv);
    return formDiv;
  }

  const makeButtons = () =>{
    const buttonRow = document.createElement('div');
    buttonRow.classList = "row";
    buttonArray = new Array(
      makeButton('Save', uploadConfig, 'button-primary'),
      makeButton('Stop & Reset', stopResetReport),
      makeButton('Json Config', viewConfigFile),
      makeButton('Restart CherryPy Server', restartCp),
    );
    buttonArray.forEach((button)=>{
      buttonRow.appendChild(button);
    });
    return buttonRow;
  }

  const makeTextArea = (tests, id) => {
    const newTextArea = document.createElement('textarea');
    newTextArea.setAttribute("rows", "40");
    newTextArea.id = id;
    newTextArea.value = tests;
    newTextArea.classList = 'u-full-width setup-input';
    const newColInput = document.createElement('div');
    newColInput.classList = 'nine columns';
    newColInput.appendChild(newTextArea);
    const newColText = document.createElement('div');
    newColText.classList = 'three columns capitalize';
    newColText.appendChild(document.createTextNode("Tests :"));
    const newRow = document.createElement('div');
    newRow.className = 'row';
    newRow.appendChild(newColText);
    newRow.appendChild(newColInput);
    return newRow;
  }

  const makeParagraphs = (content, div) => {
    if (typeof content == 'string'){
      div.appendChild(makeParagraph(content));
    }
    if (Array.isArray(content)){
      content.forEach((para) => {
        div.appendChild(makeParagraph(para));
      });
    }
    div.appendChild(document.createElement('hr'));
    return div;
  }

  const makeParagraph = (text, classes="") => {
    const newPara = document.createElement('p');
    if (classes){
      newPara.classList = classes;
    }
    newPara.innerHTML = text;
    return newPara;
  }

  const makeInput = (text, value) => {
    const newInput = document.createElement('input');
    newInput.setAttribute("type", "text");
    newInput.id = `settings-${text}`;
    newInput.classList = 'setup-input';
    newInput.value = value;
    const newColInput = document.createElement('div');
    newColInput.classList = 'nine columns';
    newColInput.appendChild(newInput);
    const newColText = document.createElement('div');
    newColText.classList = 'three columns capitalize';
    newColText.appendChild(document.createTextNode(`${text} : `));
    const newRow = document.createElement('div');
    newRow.className = 'row';
    newRow.appendChild(newColText);
    newRow.appendChild(newColInput);
    return newRow;
  }

  const makeButton = (text, func, classes="") => {
    const newButton = document.createElement('button');
    newButton.classList = classes;
    newButton.appendChild(document.createTextNode(text));
    newButton.addEventListener("click", func);
    return newButton;
  }

  // ============================================ General Info Handling/Scanning

  const getSetupPayload = () => {
    const setupPayload = {};
    let setupElements = document.querySelector(domSelectors.setupInfo);
    setupElements = setupElements.getElementsByClassName('setup-input');
    for (let element of setupElements){
      if (element.id == "settings-tests"){
        setupPayload['tests'] = objectifyTests(element.value);
      }else{
        setupPayload[key = element.id.split('-')[1]] = element.value;
      }
    }
    return setupPayload;
  }

  const objectifyTests = (rawData) => {
    const tests = [];
    rawData = rawData.trim().split('\n');
    rawData.forEach((test) => {
      test = test.trim();
      let active = true
      if (test[0] == '#'){
        active = false
      }
      test = test.replace('#', '').split(/ :|;|: /g);
      if (test.length == 3) {
        newTest = {
          'host': test[0].trim(),
          'desc': test[1].trim(),
          'test': test[2].toUpperCase().trim(),
          'active': active
        }
        tests.push(newTest);
      }
    });
    return tests;
  }

  const textifyTests = (tests, includeConfig=false) => {
    let testConfig = "";
    if (includeConfig){
      testConfig += `>> ${tests.heading} : ${tests.colour} : ${tests.interval}\n`;
    }
    tests.tests.forEach((test) => {
      hash = '# ';
      if (test['active']){
        hash = '';
      }
      testConfig += `${hash}${test['host']} ; ${test['desc']} ; ${test['test']}\n`;
    })
    return testConfig;
  }

  const doneFunc = () => {
    updateMessage('');
  }

  return {
  // ============================================= Public methods and attributes
  // =====================    Things made public
    startUI: startUI,
    setServerIndicator: setServerIndicator,
  }
})(client);

// ============================================================ Start Everything
UICtrl.startUI()