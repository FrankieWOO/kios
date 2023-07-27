#include "behavior_tree/node_list.hpp"

namespace Insertion
{
    TreeRoot::TreeRoot()
    {
        m_context_ptr = std::make_shared<ActionNodeContext>();
        initialize_tree();
    }
    void TreeRoot::register_node()
    {
        // static GripperInterface grip_singleton;
        // factory.registerSimpleCondition("CheckBattery", std::bind(CheckBattery));
        // factory.registerSimpleAction("OpenGripper", std::bind(&GripperInterface::open, &grip_singleton));
        m_factory.registerNodeType<Approach>("Approach", m_context_ptr);
        // factory.registerNodeType<Reach>("Reach");
    }
    void TreeRoot::initialize_tree()
    {
        register_node();
        m_tree = m_factory.createTreeFromText(test_tree);
    }
    std::shared_ptr<ActionNodeContext> TreeRoot::get_context_ptr()
    {
        return m_context_ptr;
    }

    BT::NodeStatus TreeRoot::tick_once()
    {
        return m_tree.tickOnce();
    }
    BT::NodeStatus TreeRoot::tick_while_running()
    {
        return m_tree.tickWhileRunning();
    }

} // namespace Insertion

////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////