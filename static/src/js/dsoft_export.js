openerp.dsoft_accounting = function (instance, local) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;



    instance.web.ActionManager && instance.web.ActionManager.include({

	 ir_actions_act_url: function (action) {

	     if (action.name && action.name.indexOf("DSOFT") >= 0) {
		 var c = instance.webclient.crashmanager;
		 return this.session.get_file({
		     url: action.url,
		     data: {data: JSON.stringify({
			 model: action.context.active_model,
			 ids: action.context['active_ids'],
			 context: action.context
		     })},
		     complete: instance.web.unblockUI,
		     error: c.rpc_error.bind(c),
		 });
	     }
	     return this._super.apply(this, arguments);
	 }
    });

};
