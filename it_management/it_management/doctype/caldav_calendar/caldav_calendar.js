// Copyright (c) 2020, IT-Geräte und IT-Lösungen wie Server, Rechner, Netzwerke und E-Mailserver sowie auch Backups, and contributors
// For license information, please see license.txt

frappe.ui.form.on('CalDav Calendar', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button('Calendar', function () { frm.trigger('sync_calendar') }, __("Sync"));
		}
	},
	sync_calendar: function(frm){

		let account = frappe.get_doc("CalDav Account",frm.doc.caldav_account);

		frappe.call({
			method: "it_management.api.sync_calendar",
			args : { 'data' : {
				"url" : account.url,
				"username" : account.username,
				"password" : account.password,
				"calendarurl" : frm.doc.calendar_url,
				"caldavcalendar" : frm.doc.name
			   }
			},
			callback: function(response_json){
			   console.log(json);
			}
		 });
	}
});
