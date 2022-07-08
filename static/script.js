'use strict';
window.addEventListener('load', function () {

  //Signout Button On-Click event handler
  document.getElementById('sign-out').onclick = function () {
    // ask firebase to sign out the user
    firebase.auth().signOut().then(function(){
      window.location.replace("/")
    });
  };

  var uiConfig = {
    signInSuccessUrl: '/', //redirect here after login
    signInOptions: [firebase.auth.EmailAuthProvider.PROVIDER_ID]  //Sing-in options -> Email
  };

  //Authentication state change
  firebase.auth().onAuthStateChanged(function (user) {
    //if login
    if (user) {
      document.getElementById('user-info').hidden = false; //hide welcome user
      document.getElementById('login-info').hidden = false; //show login info
      console.log('Signed in as ${user.displayName} (${user.email})');  //show name and email on console
      user.getIdToken().then(function (token) {
        document.cookie = "token=" + token;
        //document.cookie = "token=" + token + ";path=/";
      });
    } else {  //if logged out
      var ui = new firebaseui.auth.AuthUI(firebase.auth()); //create new ui
      ui.start('#firebase-auth-container', uiConfig); //launch ui
      document.getElementById('user-info').hidden = true; //hide welcome user
      document.getElementById('login-info').hidden = true;  //hide login info
      document.cookie = "token=";
      //document.cookie = "token=;path=/";
    }
  }, function (error) { //show error on console
    console.log(error);
    alert('Unable to log in: ' + error);
  });

});


