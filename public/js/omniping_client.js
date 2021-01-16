
class ApiClient{
  // initialise the client Session:
  constructor(){
    this.status = 0;
  }
  
  // GET Method
  async get(url){
    return await this.request(url, 'GET');
  }
  
  // POST Method
  async post(url, data){
    return await this.request(url, 'POST', data);
  }

  // PUT method
  async put(url, data){
    return await this.request(url, 'PUT', data);
  }
  
  // DELETE Method
  async delete(url, data){
    return await this.request(url, 'DELETE', data);
  }
  
  // generic method
  async request(url, verb, data){
    UICtrl.setServerIndicator("err");
    const params = {};
    params['method'] = verb;
    if (verb !== "GET"){
      params['headers'] = {'Content-type': 'application/json'};
      params['body'] = JSON.stringify(data);
    }
    const response = await fetch(url, params);
    this.status = response.status;
    if (!response.ok){
      let mess;
      try {
        let resp = await response.json();
        mess = resp.message;
      } catch(err) {
        mess = response.statusText;
      }
      UICtrl.setServerIndicator("err");
      throw new ApiError(response.status, mess);
    } else {
      UICtrl.setServerIndicator("on");
      return await response.json();
    }
  }
}

class ApiError extends Error{
  constructor (respStatCode, respStatText){
    const message = `${respStatText} (${respStatCode})`;
    UICtrl.setServerIndicator("bad");
    super(message);
  }
}