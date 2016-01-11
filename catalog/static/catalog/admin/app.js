'use strict';


var templateHelper = function(templateName, data){
    return _.template($('#'+templateName).html(), data)
}


var delete_tree_item = function(node, tree){
    var item_id = node.id
    $.ajax({
        url: 'delete/' + item_id,
        success: function(data){
            tree.delete_node(node);
        }
    });
}


var move_tree_item = function(item_id, target_id, position){
    $.ajax({
        url: 'move/' + item_id,
        data: {'position': position, 'target_id': target_id},
    });
}


var CatalogApp = {};


CatalogApp.ItemModel = Backbone.Model.extend({});


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
        console.log(response, xhr);
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
    template: 'table_items_tpl',
    initialize: function(options){
        if(options.parent_id){
            this.parent_id = options.parent_id;
        } else {
            this.parent_id = '';
        }

        this.collection = new CatalogApp.ItemCollection({
            parent_id: this.parent_id
        });

        this.listenTo(this.collection, 'reset', this.render);
        console.log();
    },
    render: function(){
        self = this;
        this.$el.html(
            templateHelper(
                this.template,
                {fields: this.collection.fields, items: this.collection.toJSON()}
            )
        );
        $(document).ready(function(){
            $(self.tableEl).tablesorter({
                sortList: [[0,0]]
            });
        });
        return this
    },
    reRender: function(options){
        this.collection.changeParentId(options.parent_id);
        $(this.tableEl).trigger('destroy');
        return this
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
                }
            },
            'search': {
                'show_only_matches': true,
                'show_only_matches_children': true,
                'fuzzy': true
            },
            'contextmenu': {
                'items': function(node){
                    var tree = self.$el.jstree(true);
                    return {
                        'Remove': {
                            'separator_before': false,
                            'separator_after': false,
                            'label': 'Удалить',
                            'icon': 'delete-item',
                            'action': function (obj) {
                                self.deleteTreeItem(obj, node, tree);
                            }
                        }
                    }
                }
            },
            'plugins' : [ 'dnd', 'search', 'types' ]
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
    deleteTreeItem: function(obj, node, tree){
        if(confirm('Вы уверенны? (если внутри обьекта есть другие обьекты они будут удалены)')){
            delete_tree_item(node, tree);
        }
    },
    checkTreeCallbacks: function(operation, node, parent, position, more){
        if (operation === "move_node" && more && more.core) {
            console.log(operation, parent, node, position, more);
            if(confirm('Вы уверенны?')){
                if(parent.children.length !== 0){
                    _.each(parent.children, function(child_id){
                        console.log(this);
                        console.log(parent.children.indexOf(this.get_node(child_id).id),this.get_node(child_id).text);
                    }, this);
                } else {
                    move_tree_item(node.id, parent.id, 'first-child');
                }
                return true
            }
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
