'use strict';


var templateHelper = function(templateName, data){
    return _.template($('#'+templateName).html(), data)
}

function addMessage(type, text) {
    var message = $('<li class="' + type + '">' + text + '</li>').hide();
    $(".messagelist").append(message);
    message.fadeIn(500);

    setTimeout(function() {
        message.fadeOut(500, function() {
            message.remove();
        });
    }, 5000);
}

var delete_tree_item = function(node, tree){
    var item_id = node.id
    $.ajax({
        url: 'delete/' + item_id,
        success: function(data) {
            if (data.status === 'OK') {
                tree.delete_node(node);
            }
            addMessage(data.type_message, data.message);
        }
    });
}

var move_tree_item = function(item_id, target_id, position){
    var moving = false;
    $.ajax({
        url: 'move/' + item_id,
        data: {'position': position, 'target_id': target_id},
        async: false,
        beforeSend: function() {
            $('#overlay').fadeIn();
        },
        success: function(data){
            if (data.status === 'OK') {
                moving = true;
                addMessage(data.type_message, data.message);
            }
            else {
                moving = false;
                addMessage(data.type_message, data.message);
            }
            $('#overlay').fadeOut();
        }
    });
    return moving;
}


var CatalogApp = {};
var csrftoken = $.cookie('csrftoken');

CatalogApp.ItemModel = Backbone.Model.extend({
    sync: function(method, model, options) {
        if (method === "update") {
            options.url = "edit/";
            options.beforeSend = function(xhr){
                if (!this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                }
            };
            return Backbone.sync(method, model, options);
        }
    },
    parse : function(response, xhr) {
        if (response.status) {
            this.status = response.status;
            addMessage(response.type_message, response.message);
            return {};
        }
        else {
            return response;
        }
    }
});

CatalogApp.EditView = Backbone.View.extend({
    tagName: 'td',
    className: 'editable',
    template: 'field_tpl',
    edit_template: 'edit_tpl',
    events: {
        'click': 'active_edit',
        'click .accept': 'accept_edit',
        'click .cancel': 'cancel_edit',
    },
    initialize: function(options) {
        if(options.field_name){
            this.field_name = options.field_name;
        }
    },
    render: function() {
        this.$el.html(
            templateHelper(
                this.template,
                {field: this.model.get(this.field_name)}
            )
        );
        this.$el.removeClass('active-edit');
        return this;
    },
    renderEdit: function() {
        this.$el.html(
            templateHelper(
                this.edit_template,
                {type: this.model.get(this.field_name).type,
                 value: this.model.get(this.field_name).value}
            )
        );
        this.$el.addClass('active-edit');
        this.$el.find('input').focus().val(this.model.get(this.field_name).value);
        return this;
    },
    close: function() {
        this.remove();
        this.unbind();
    },
    active_edit: function(event){
        if (!this.$el.hasClass('active-edit')) {
            this.renderEdit();
        }
    },
    cancel_edit: function(event){
        event.stopPropagation();
        this.render();
    },
    accept_edit: function(event){
        event.stopPropagation();
        var new_value;
        if (this.model.get(this.field_name).type == 'checkbox') {
            if (this.$el.find('input').prop("checked")) new_value = 't';
            else new_value = 'f';
        } else {
            new_value = this.$el.find('input').val();
        }
        if (this.model.get(this.field_name).value != new_value) {
            this.model.set(this.field_name, {'editable': true, 'type': this.model.get(this.field_name).type, 'value': new_value});
            this.$el.addClass('accept_value');
        }
        this.render();
    }
});

CatalogApp.ItemView = Backbone.View.extend({
    tagName: 'tr',
    template: 'item_tpl',
    events: {
        'click .save_item': 'save',
    },
    initialize: function(options){
        if(options.fields && options.list_view){
            this.fields = options.fields;
            this.list_view = options.list_view;
        }
        this.child_views = [];
    },
    render: function () {
        this.$el.empty();
        this.fields.forEach(function(field){
            this.renderField(field[0]);
        }, this);
        this.$el.append('<td><a class="save_item">Сохранить</a></td>')
        return this;
    },
    renderField: function(field_name) {
        var field = this.model.get(field_name)
        if (field.editable) {
            var editview = new CatalogApp.EditView({
                model: this.model,
                field_name: field_name
            });
            this.$el.append(editview.render().el);
        }
        else {
            this.$el.append(
                templateHelper(
                    this.template,
                    {field: field}
                )
            );
        }
    },
    close: function() {
        this.remove();
        this.unbind();
        _.each(this.child_views, function(child_view){
            if (child_view.close){
                child_view.close();
            }
        });
    },
    save: function(event) {
        var self = this;
        this.model.save({},
            {
                success: function(model, response, options){
                    console.log(model);
                    if (model.status === 'OK') {
                        model.status = '';
                        self.render();
                        $(self.list_view.tableEl).trigger('update');
                    }
                }
            }
        );
    }
});

CatalogApp.ItemCollection = Backbone.Collection.extend({
    model: CatalogApp.ItemModel,
    initialize: function(options){
        if(options.parent_id){
            this.parent_id = options.parent_id;
        } else {
            this.parent_id = '';
        }
        this.fetch({reset: true});
    },
    url: function(){
        return 'list_children/' + this.parent_id
    },
    parse: function(response, xhr){
        this.fields = response.fields;
        return response.nodes
    },
    changeParentId: function(parent_id){
        this.parent_id = parent_id;
        this.fetch({reset: true});
    }
});

CatalogApp.ListItemsView = Backbone.View.extend({
    el: '#list_items_container',
    tableEl: '#list_table',
    tbodyEl: '#list_table tbody',
    template: 'table_items_tpl',
    initialize: function(options){
        var self = this;
        if(options.parent_id){
            this.parent_id = options.parent_id;
        } else {
            this.parent_id = '';
        }

        this.collection = new CatalogApp.ItemCollection({
            parent_id: this.parent_id
        });
        this.child_views = [];
        this.listenTo(this.collection, 'reset', this.render);
        this.listenTo(this, 'afterRender', this.initSorter);
    },
    render: function(){
        this.item_views = [];
        this.$el.html(
            templateHelper(
                this.template,
                {fields: this.collection.fields}
            )
        );
        this.collection.each(function( item ){
            this.renderItem( item );
        }, this);
        this.trigger('afterRender');
        return this
    },
    renderItem: function(item) {
        var itemview = new CatalogApp.ItemView({
            model: item,
            list_view: this,
            fields: this.collection.fields
        });
        $(this.tbodyEl).append(itemview.render().el);
        this.child_views.push(itemview);
    },
    reRender: function(options){
        $(this.tableEl).trigger("destroy");
        this.close_child_views();
        this.item_views.forEach(function(view){
            console.log(view.remove());
        });
        this.collection.changeParentId(options.parent_id);
        return this
    },
    close_child_views: function() {
        _.each(this.child_views, function(child_view){
            if (child_view.close) child_view.close();
        });
    },
    initSorter: function(){
        self = this;
        $(document).ready(function(){
            $(self.tableEl).tablesorter({
                sortList: [[0,0]],
                theme: 'ice',
                widgets: ['resizable'],
                textExtraction:function(s){
                    if($(s).find('img').length == 0) return $(s).text();
                    return $(s).find('img').attr('alt');
                }
            });
        });
    }
});


CatalogApp.TreeView = Backbone.View.extend({
    el: '#tree_container',
    searchId: '#tree_search',
    template: 'tree_tpl',
    initialize: function(options){
        var self = this;

        this.render();

        if(Modernizr.localstorage){
            this.resizeColumns($('#left-col'), localStorage['resize_width']);
        }

        $("#catalog-root-btn").click(function(event){
            $(".jstree-clicked").removeClass("jstree-clicked");
            self.renderListItemsView();
        });

        $(window).resize(function(event){
            self.resizeColumns($("#left-col"));

        });
        $("#left-col").resizable({
            handles: 'e',
            resize: function(e, ui){
                self.resizeColumns(this);
            },
            stop: function(e, ui){
                if(Modernizr.localstorage){
                    localStorage['resize_width'] = $(this).width().toString();
                }
            }
        });
    },
    render: function(){
        this.initJsTree();
        return this;
    },
    resizeColumns: function(el, width){
        var parent_width = $(el).parent().outerWidth();
        if(width){
            var width = parseInt(width)
            $(el).width(width);
            $('#right-col').width(parent_width - parseInt(width)-4);
        } else {
            var left_width = $(el).outerWidth();
            $('#right-col').width(parent_width - left_width-2);
        }
    },
    initJsTree: function(){
        var self = this;
        this.$el.jstree({
            'core' : {
                'check_callback' : self.checkTreeCallbacks,
                'animation': 0,
                'data': {
                    'url': 'tree/',
                }

            },
            'types': {
                'leaf': {
                    'max_depth': '0',
                    'icon': 'jstree-file',
                },
            },
            'search': {
                'show_only_matches': true,
                'show_only_matches_children': true
            },
            'contextmenu': {
                'items': function(node){
                    var tree = self.$el.jstree(true);
                    var submenu = {};
                    _.each(node.data.add_links, function(link) {
                        var menu_item = {};
                        menu_item.label = link.label;
                        menu_item.action = function () {
                            self.addTreeItem(link.url);
                        }
                        submenu[link.label]=menu_item;
                    });

                    return {
                        'Remove': {
                            'separator_before': false,
                            'separator_after': false,
                            'label': 'Удалить',
                            'icon': 'delete-item',
                            'action': function (obj) {
                                self.deleteTreeItem(obj, node, tree);
                            }
                        },
                        'Edit': {
                            'label': 'Изменить',
                            'icon': 'edit-item',
                            'action': function () {
                                self.changeTreeItem(node);
                            }
                        },
                        'Add': {
                            'label': 'Добавить',
                            'submenu': submenu,
                            '_disabled': node.type === 'leaf'
                        },
                        'Copy': {
                            'label': 'Копировать',
                            'action': function() {
                                self.copyTreeItem(node, tree);
                            }
                        }
                    }
                }
            },
            'plugins' : [ 'dnd', 'search', 'types', 'contextmenu', 'state']
        });

        this.$el.on('select_node.jstree', function(e, data){
            if(data.node.children.length > 0){
                self.renderListItemsView(data.node.id);
            }
        });

        // search
        var to = false;
        $(self.searchId).keyup(function(e){
            if(e.which == 27){ //escape clear
                self.$el.jstree(true).clear_search();
                $(this).val('');
                return;
            }

            if(to) clearTimeout(to);
            to = setTimeout(function(){
                var v = $(self.searchId).val();
                self.$el.jstree(true).search(v);
            }, 300);
        });

        return this;
    },
    addTreeItem: function(url) {
        var win = window.open(url + '&_popup=1', '', "width=800,height=500,resizable=yes,scrollbars=yes,status=yes");
        win.focus();
    },
    changeTreeItem: function(node){
        var win = window.open(node.data.change_link + '?_popup=1', '', "width=800,height=500,resizable=yes,scrollbars=yes,status=yes");
        win.focus();
    },
    deleteTreeItem: function(obj, node, tree){
        if(confirm('Вы уверенны? (если внутри обьекта есть другие обьекты они будут удалены)')){
            delete_tree_item(node, tree);
        }
    },
    copyTreeItem: function(node, tree) {
        var win = window.open(node.data.copy_link + '&_popup=1', '', "width=800,height=500,resizable=yes,scrollbars=yes,status=yes");
        win.focus();
    },
    checkTreeCallbacks: function(operation, node, parent, position, more){
        if (operation === "move_node" && more && more.core) {
            var moving = false;
            if(parent.children.length !== 0){
                var i = 0;
                _.each(parent.children, function(child_id){
                    var target = this.get_node(child_id);
                    var parent_target = this.get_node(target.parent);
                    if (position === $.inArray(target.id, parent_target.children)) {
                        moving = move_tree_item(node.id, target.id, 'left');
                    }
                    if (i === parent.children.length - 1 && position === parent.children.length) {
                        moving = move_tree_item(node.id, target.id, 'right');
                    }
                    i++;
                }, this);
            } else {
                moving = move_tree_item(node.id, parent.id, 'last-child');
            }
            return moving;
        }
    },
    renderListItemsView: function(tree_id){
        if(this.listItemsView){
            this.listItemsView.reRender({
                parent_id: tree_id
            });
        } else {
            this.listItemsView = new CatalogApp.ListItemsView({
                parent_id: tree_id
            });
        }
    }
});


$(document).ready(function(){
    var catalogTreeOneView = new CatalogApp.TreeView({});
});
