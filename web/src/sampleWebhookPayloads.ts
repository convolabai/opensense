export interface SamplePayload {
  name: string;
  source: string;
  payload: any;
}

export const samplePayloads: Record<string, SamplePayload> = {
  // GitHub Events
  github_pr_opened: {
    name: "GitHub - Pull Request Opened",
    source: "github",
    payload: {
      action: "opened",
      number: 1374,
      pull_request: {
        id: 1374,
        number: 1374,
        title: "Add new feature",
        state: "open",
        user: { login: "alice", id: 12345 },
        body: "This PR adds a new feature to the application.",
        head: { ref: "feature-branch", sha: "abc123" },
        base: { ref: "main", sha: "def456" }
      },
      repository: { 
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo",
        private: false
      },
      sender: { login: "alice", id: 12345 }
    }
  },
  github_pr_merged: {
    name: "GitHub - Pull Request Merged",
    source: "github",
    payload: {
      action: "closed",
      number: 1374,
      pull_request: {
        id: 1374,
        number: 1374,
        title: "Add new feature",
        state: "closed",
        merged: true,
        user: { login: "alice", id: 12345 },
        merged_by: { login: "bob", id: 67890 }
      },
      repository: { 
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },
  github_push: {
    name: "GitHub - Push to Repository",
    source: "github",
    payload: {
      ref: "refs/heads/main",
      before: "abc123",
      after: "def456",
      commits: [
        {
          id: "def456",
          message: "Fix bug in authentication",
          author: { name: "Alice", email: "alice@example.com" },
          url: "https://github.com/alice/test-repo/commit/def456"
        }
      ],
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      },
      pusher: { name: "alice", email: "alice@example.com" }
    }
  },
  github_issue_opened: {
    name: "GitHub - Issue Opened",
    source: "github",
    payload: {
      action: "opened",
      issue: {
        id: 987654,
        number: 42,
        title: "Bug in user registration",
        body: "Users are unable to register with special characters in their email.",
        state: "open",
        user: { login: "alice", id: 12345 },
        labels: [{ name: "bug", color: "d73a4a" }]
      },
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },
  github_release_published: {
    name: "GitHub - Release Published",
    source: "github",
    payload: {
      action: "published",
      release: {
        id: 567890,
        tag_name: "v1.2.0",
        name: "Version 1.2.0",
        body: "## What's New\n- Added new features\n- Fixed bugs",
        draft: false,
        prerelease: false,
        created_at: "2024-01-01T12:00:00Z",
        published_at: "2024-01-01T12:00:00Z",
        author: { login: "alice", id: 12345 }
      },
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },
  github_pr_review_1234_approved: {
    name: "GitHub - PR 1234 Review Approved",
    source: "github",
    payload: {
      action: "submitted",
      review: {
        id: 12345678,
        user: { login: "alice", id: 12345 },
        body: "Looks good to me!",
        state: "approved",
        submitted_at: "2024-01-01T12:00:00Z"
      },
      pull_request: {
        id: 1234,
        number: 1234,
        title: "Fix bug in authentication",
        state: "open",
        user: { login: "bob", id: 67890 }
      },
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },
  github_pr_review_1374_title_change: {
    name: "GitHub - PR 1374 Title Changed",
    source: "github",
    payload: {
      action: "edited",
      changes: {
        title: {
          from: "Old title"
        }
      },
      pull_request: {
        id: 1374,
        number: 1374,
        title: "Updated feature implementation",
        state: "open",
        user: { login: "bob", id: 67890 }
      },
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },
  github_pr_review_1374_approved: {
    name: "GitHub - PR 1374 Review Approved",
    source: "github",
    payload: {
      action: "submitted",
      review: {
        id: 12345679,
        user: { login: "alice", id: 12345 },
        body: "Great work!",
        state: "approved",
        submitted_at: "2024-01-01T12:00:00Z"
      },
      pull_request: {
        id: 1374,
        number: 1374,
        title: "Add new feature",
        state: "open",
        user: { login: "bob", id: 67890 }
      },
      repository: {
        id: 12345,
        name: "test-repo",
        full_name: "alice/test-repo"
      }
    }
  },

  // Slack Events
  slack_message: {
    name: "Slack - Message Posted",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "message",
        channel: "C123456789",
        user: "U123456789",
        text: "Hello team! Here's the update on our project.",
        ts: "1234567890.123456"
      },
      team_id: "T123456789"
    }
  },
  slack_file_shared: {
    name: "Slack - File Shared",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "file_shared",
        file_id: "F06A2G45T",
        user_id: "U123456789",
        file: {
          id: "F06A2G45T",
          name: "design.png",
          title: "New Design Mockup",
          mimetype: "image/png",
          filetype: "png",
          size: 1024000
        },
        channel_id: "C123456789"
      }
    }
  },
  slack_user_joined: {
    name: "Slack - User Joined Channel",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "member_joined_channel",
        user: "U123456789",
        channel: "C123456789",
        channel_type: "C",
        team: "T123456789",
        inviter: "U987654321"
      }
    }
  },
  slack_app_mention: {
    name: "Slack - App Mention",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "app_mention",
        user: "U123456789",
        text: "<@U0LAN0Z89> can you help with this task?",
        ts: "1234567890.123456",
        channel: "C123456789",
        event_ts: "1234567890.123456"
      },
      team_id: "T123456789"
    }
  },
  slack_message_not_file: {
    name: "Slack - Regular Message",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "message",
        channel: "C123456789",
        user: "U123456789",
        text: "Hey everyone, just sharing a quick update on the project status.",
        ts: "1234567890.123456"
      },
      team_id: "T123456789"
    }
  },
  slack_file_upload_no_context: {
    name: "Slack - File Upload No Context",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "file_shared",
        file_id: "F456789",
        user_id: "U123456789",
        file: {
          id: "F456789",
          name: "random_image.jpg",
          title: "",
          mimetype: "image/jpeg",
          filetype: "jpg",
          size: 2048000
        },
        channel_id: "C123456789"
      },
      team_id: "T123456789"
    }
  },
  slack_file_upload_important: {
    name: "Slack - Important Document Upload",
    source: "slack",
    payload: {
      type: "event_callback",
      event: {
        type: "file_shared",
        file_id: "F789012",
        user_id: "U123456789",
        file: {
          id: "F789012",
          name: "quarterly_report.pdf",
          title: "Q4 Financial Report",
          mimetype: "application/pdf",
          filetype: "pdf",
          size: 5120000
        },
        channel_id: "C123456789"
      },
      team_id: "T123456789"
    }
  },
  email_newsletter: {
    name: "Email - Newsletter",
    source: "email",
    payload: {
      messageId: "email_123",
      from: "newsletter@example.com",
      to: "user@company.com",
      subject: "Weekly Newsletter - Tech Updates",
      body: "This week in tech: new frameworks, AI updates, and more!",
      timestamp: "2024-01-01T12:00:00Z",
      headers: {
        "List-Unsubscribe": "mailto:unsubscribe@example.com"
      }
    }
  },
  email_fyi_from_ceo: {
    name: "Email - FYI from CEO",
    source: "email",
    payload: {
      messageId: "email_456",
      from: "ceo@company.com",
      to: "user@company.com",
      subject: "FYI: Draft for later review",
      body: "Hey team, here's a draft document for your review when you have time. No rush on this one.",
      timestamp: "2024-01-01T12:00:00Z",
      headers: {}
    }
  },
  email_urgent_from_client: {
    name: "Email - Urgent from Client",
    source: "email",
    payload: {
      messageId: "email_789",
      from: "client@important-customer.com",
      to: "user@company.com",
      subject: "URGENT: Production system down",
      body: "Our production system is experiencing critical issues. Please respond immediately.",
      timestamp: "2024-01-01T12:00:00Z",
      priority: "high",
      headers: {
        "Importance": "high"
      }
    }
  },

  // Atlassian Jira Events
  jira_issue_created: {
    name: "Jira - Issue Created",
    source: "jira",
    payload: {
      timestamp: 1640995200000,
      webhookEvent: "jira:issue_created",
      issue: {
        id: "10001",
        key: "PROJ-123",
        fields: {
          summary: "Fix login page styling",
          description: "The login page has styling issues on mobile devices.",
          issuetype: { name: "Bug", id: "1" },
          priority: { name: "High", id: "2" },
          status: { name: "To Do", id: "1" },
          assignee: { displayName: "John Doe", emailAddress: "john@company.com" },
          reporter: { displayName: "Jane Smith", emailAddress: "jane@company.com" },
          project: { key: "PROJ", name: "Project Alpha" }
        }
      }
    }
  },
  jira_issue_updated: {
    name: "Jira - Issue Updated",
    source: "jira",
    payload: {
      timestamp: 1640995200000,
      webhookEvent: "jira:issue_updated",
      issue: {
        id: "10001",
        key: "PROJ-123",
        fields: {
          summary: "Fix login page styling",
          status: { name: "In Progress", id: "3" },
          assignee: { displayName: "John Doe", emailAddress: "john@company.com" }
        }
      },
      changelog: {
        items: [
          {
            field: "status",
            fieldtype: "jira",
            from: "1",
            fromString: "To Do",
            to: "3",
            toString: "In Progress"
          }
        ]
      }
    }
  },
  jira_issue_to_in_progress: {
    name: "Jira - Issue Moved to In Progress",
    source: "jira",
    payload: {
      timestamp: 1640995200000,
      webhookEvent: "jira:issue_updated",
      issue: {
        id: "10123",
        key: "PROJ-123",
        fields: {
          summary: "Implement new authentication flow",
          status: { name: "In Progress", id: "3" },
          assignee: { displayName: "Alice Smith", emailAddress: "alice@company.com" }
        }
      },
      changelog: {
        items: [
          {
            field: "status",
            fieldtype: "jira",
            from: "1",
            fromString: "To Do",
            to: "3",
            toString: "In Progress"
          }
        ]
      }
    }
  },
  jira_issue_done_unassigned: {
    name: "Jira - Issue Moved to Done (Unassigned)",
    source: "jira",
    payload: {
      timestamp: 1640995200000,
      webhookEvent: "jira:issue_updated",
      issue: {
        id: "10456",
        key: "PROJ-456",
        fields: {
          summary: "Update documentation",
          status: { name: "Done", id: "6" },
          assignee: null
        }
      },
      changelog: {
        items: [
          {
            field: "status",
            fieldtype: "jira",
            from: "3",
            fromString: "In Progress",
            to: "6",
            toString: "Done"
          }
        ]
      }
    }
  },
  jira_issue_done_by_owner: {
    name: "Jira - Issue Moved to Done by Owner",
    source: "jira",
    payload: {
      timestamp: 1640995200000,
      webhookEvent: "jira:issue_updated",
      issue: {
        id: "10789",
        key: "PROJ-789",
        fields: {
          summary: "Implement payment processing",
          status: { name: "Done", id: "6" },
          assignee: { displayName: "Product Owner", emailAddress: "po@company.com" }
        }
      },
      changelog: {
        items: [
          {
            field: "status",
            fieldtype: "jira",
            from: "3",
            fromString: "In Progress",
            to: "6",
            toString: "Done"
          }
        ]
      }
    }
  },

  // Twilio Events
  twilio_sms_received: {
    name: "Twilio - SMS Received",
    source: "twilio",
    payload: {
      MessageSid: "SM1234567890abcdef1234567890abcdef",
      AccountSid: "SAMPLEACCOUNTID",
      From: "+15551234567",
      To: "+15559876543",
      Body: "Hello, this is a test message!",
      MessageStatus: "received",
      NumMedia: "0",
      FromCity: "NEW YORK",
      FromState: "NY",
      FromCountry: "US",
      ToCity: "SAN FRANCISCO",
      ToState: "CA",
      ToCountry: "US"
    }
  },
  twilio_call_completed: {
    name: "Twilio - Call Completed",
    source: "twilio",
    payload: {
      CallSid: "CA1234567890abcdef1234567890abcdef",
      AccountSid: "SAMPLEACCOUNTID",
      From: "+15551234567",
      To: "+15559876543",
      CallStatus: "completed",
      CallDuration: "45",
      Direction: "inbound",
      FromCity: "NEW YORK",
      FromState: "NY",
      FromCountry: "US",
      ToCity: "SAN FRANCISCO",
      ToState: "CA",
      ToCountry: "US"
    }
  },

  // Discord Events
  discord_message_create: {
    name: "Discord - Message Created",
    source: "discord",
    payload: {
      id: "1234567890123456789",
      type: 0,
      content: "Hello everyone! How's the project going?",
      channel_id: "9876543210987654321",
      author: {
        id: "1111111111111111111",
        username: "alice",
        discriminator: "1234",
        avatar: "avatar_hash"
      },
      timestamp: "2024-01-01T12:00:00.000000+00:00",
      guild_id: "5555555555555555555"
    }
  },
  discord_member_join: {
    name: "Discord - Member Joined",
    source: "discord",
    payload: {
      guild_id: "5555555555555555555",
      user: {
        id: "2222222222222222222",
        username: "newuser",
        discriminator: "5678",
        avatar: "avatar_hash"
      },
      nick: null,
      roles: [],
      joined_at: "2024-01-01T12:00:00.000000+00:00",
      premium_since: null,
      deaf: false,
      mute: false
    }
  },

  // Stripe Events
  stripe_payment_succeeded: {
    name: "Stripe - Payment Succeeded",
    source: "stripe",
    payload: {
      id: "evt_1234567890",
      object: "event",
      type: "payment_intent.succeeded",
      data: {
        object: {
          id: "pi_3OrFAb47K1Z2xQ8C0123",
          object: "payment_intent",
          amount: 2000,
          currency: "usd",
          status: "succeeded",
          customer: "cus_1234567890",
          description: "Subscription payment",
          metadata: {
            order_id: "order_123"
          }
        }
      },
      created: 1640995200
    }
  },
  stripe_customer_created: {
    name: "Stripe - Customer Created",
    source: "stripe",
    payload: {
      id: "evt_1234567890",
      object: "event",
      type: "customer.created",
      data: {
        object: {
          id: "cus_1234567890",
          object: "customer",
          email: "customer@example.com",
          name: "John Doe",
          phone: "+15551234567",
          created: 1640995200,
          metadata: {
            user_id: "user_123"
          }
        }
      },
      created: 1640995200
    }
  },
  stripe_subscription_updated: {
    name: "Stripe - Subscription Updated",
    source: "stripe",
    payload: {
      id: "evt_1234567890",
      object: "event",
      type: "customer.subscription.updated",
      data: {
        object: {
          id: "sub_1234567890",
          object: "subscription",
          customer: "cus_1234567890",
          status: "active",
          current_period_start: 1640995200,
          current_period_end: 1643673600,
          plan: {
            id: "plan_premium",
            nickname: "Premium Plan",
            amount: 2999,
            currency: "usd"
          }
        }
      },
      created: 1640995200
    }
  },
  stripe_refund_low_value: {
    name: "Stripe - Low Value Refund",
    source: "stripe",
    payload: {
      id: "evt_refund_100",
      object: "event",
      type: "charge.dispute.created",
      data: {
        object: {
          id: "re_1234",
          object: "refund",
          amount: 10000,  // $100.00
          currency: "usd",
          charge: "ch_1234567890",
          reason: "requested_by_customer",
          status: "succeeded",
          created: 1640995200,
          metadata: {
            order_id: "order_100"
          }
        }
      },
      created: 1640995200
    }
  },
  stripe_refund_high_value_test: {
    name: "Stripe - High Value Test Refund",
    source: "stripe",
    payload: {
      id: "evt_refund_800",
      object: "event",
      type: "charge.dispute.created",
      data: {
        object: {
          id: "re_5678",
          object: "refund",
          amount: 80000,  // $800.00
          currency: "usd",
          charge: "ch_test_1234567890",
          reason: "requested_by_customer",
          status: "succeeded",
          created: 1640995200,
          metadata: {
            order_id: "test_order_800",
            customer_type: "test"
          }
        }
      },
      created: 1640995200
    }
  },
  stripe_refund_high_value_real: {
    name: "Stripe - High Value Real Refund",
    source: "stripe",
    payload: {
      id: "evt_refund_1200",
      object: "event",
      type: "charge.dispute.created",
      data: {
        object: {
          id: "re_9012",
          object: "refund",
          amount: 120000,  // $1200.00
          currency: "usd",
          charge: "ch_live_1234567890",
          reason: "requested_by_customer",
          status: "succeeded",
          created: 1640995200,
          metadata: {
            order_id: "order_1200",
            customer_id: "cus_real_customer"
          }
        }
      },
      created: 1640995200
    }
  },

  // Shopify Events
  shopify_order_created: {
    name: "Shopify - Order Created",
    source: "shopify",
    payload: {
      id: 820982911946154500,
      admin_graphql_api_id: "gid://shopify/Order/820982911946154500",
      app_id: null,
      browser_ip: "0.0.0.0",
      buyer_accepts_marketing: false,
      cancel_reason: null,
      cancelled_at: null,
      cart_token: "68778783ad298f1c80c3bafcddeea02f",
      checkout_id: 901414060986,
      checkout_token: "1234567890",
      closed_at: null,
      confirmed: true,
      contact_email: "jon@example.com",
      created_at: "2024-01-01T12:00:00-04:00",
      currency: "USD",
      current_subtotal_price: "398.00",
      current_total_discounts: "0.00",
      current_total_duties_set: null,
      current_total_price: "409.94",
      current_total_tax: "11.94",
      customer_locale: "en",
      device_id: null,
      discount_codes: [],
      email: "jon@example.com",
      estimated_taxes: false,
      financial_status: "pending",
      fulfillment_status: null,
      gateway: "bogus",
      landing_site: "http://www.example.com?source=abc",
      landing_site_ref: "abc",
      location_id: null,
      name: "#1001",
      note: null,
      note_attributes: [],
      number: 1,
      order_number: 1001,
      order_status_url: "https://test-shop.myshopify.com/orders/123abc",
      original_total_duties_set: null,
      payment_gateway_names: ["bogus"],
      phone: "+557734881234",
      presentment_currency: "USD",
      processed_at: "2024-01-01T12:00:00-04:00",
      processing_method: "direct",
      reference: "fhwdgads",
      referring_site: "http://www.otherexample.com",
      source_identifier: "fhwdgads",
      source_name: "web",
      source_url: null,
      subtotal_price: "398.00",
      tags: "",
      tax_lines: [
        {
          price: "11.94",
          rate: 0.06,
          title: "State Tax"
        }
      ],
      taxes_included: false,
      test: false,
      token: "b1946ac92492d2347c6235b4d2611184",
      total_discounts: "0.00",
      total_line_items_price: "398.00",
      total_outstanding: "409.94",
      total_price: "409.94",
      total_price_usd: "409.94",
      total_shipping_price_set: {
        shop_money: {
          amount: "0.00",
          currency_code: "USD"
        },
        presentment_money: {
          amount: "0.00",
          currency_code: "USD"
        }
      },
      total_tax: "11.94",
      total_tip_received: "0.00",
      total_weight: 0,
      updated_at: "2024-01-01T12:00:00-04:00",
      user_id: null,
      billing_address: {
        first_name: "Bob",
        address1: "Chestnut Street 92",
        phone: "+1(502)-459-2181",
        city: "Louisville",
        zip: "40202",
        province: "Kentucky",
        country: "United States",
        last_name: "Norman",
        address2: "",
        company: null,
        latitude: 45.41634,
        longitude: -75.6868,
        name: "Bob Norman",
        country_code: "US",
        province_code: "KY"
      },
      customer: {
        id: 207119551,
        email: "bob.norman@example.com",
        accepts_marketing: false,
        created_at: "2024-01-01T12:00:00-04:00",
        updated_at: "2024-01-01T12:00:00-04:00",
        first_name: "Bob",
        last_name: "Norman",
        orders_count: 1,
        state: "disabled",
        total_spent: "41.94",
        last_order_id: 820982911946154500,
        note: null,
        verified_email: true,
        multipass_identifier: null,
        tax_exempt: false,
        phone: "+16136120707",
        tags: "",
        last_order_name: "#1001",
        currency: "USD"
      },
      line_items: [
        {
          id: 866550311766439020,
          admin_graphql_api_id: "gid://shopify/LineItem/866550311766439020",
          fulfillable_quantity: 1,
          fulfillment_service: "manual",
          fulfillment_status: null,
          gift_card: false,
          grams: 567,
          name: "IPod Nano - 8GB",
          origin_location: {
            id: 24826418,
            country_code: "DE",
            province_code: "",
            name: "Apple",
            address1: "Musterstraße 42",
            address2: "",
            city: "Musterstadt",
            zip: "42424"
          },
          price: "199.00",
          price_set: {
            shop_money: {
              amount: "199.00",
              currency_code: "USD"
            },
            presentment_money: {
              amount: "199.00",
              currency_code: "USD"
            }
          },
          product_exists: true,
          product_id: 632910392,
          properties: [],
          quantity: 1,
          requires_shipping: true,
          sku: "IPOD2008PINK",
          taxable: true,
          title: "IPod Nano - 8GB",
          total_discount: "0.00",
          total_discount_set: {
            shop_money: {
              amount: "0.00",
              currency_code: "USD"
            },
            presentment_money: {
              amount: "0.00",
              currency_code: "USD"
            }
          },
          variant_id: 808950810,
          variant_inventory_management: "shopify",
          variant_title: "Pink",
          vendor: "Apple"
        }
      ],
      payment_terms: null,
      refunds: [],
      shipping_address: {
        first_name: "Bob",
        address1: "Chestnut Street 92",
        phone: "+1(502)-459-2181",
        city: "Louisville",
        zip: "40202",
        province: "Kentucky",
        country: "United States",
        last_name: "Norman",
        address2: "",
        company: null,
        latitude: 45.41634,
        longitude: -75.6868,
        name: "Bob Norman",
        country_code: "US",
        province_code: "KY"
      },
      shipping_lines: []
    }
  },
  shopify_order_paid: {
    name: "Shopify - Order Paid",
    source: "shopify",
    payload: {
      id: 820982911946154500,
      financial_status: "paid",
      fulfillment_status: null,
      name: "#1001",
      total_price: "409.94",
      currency: "USD",
      customer: {
        id: 207119551,
        email: "bob.norman@example.com",
        first_name: "Bob",
        last_name: "Norman"
      },
      created_at: "2024-01-01T12:00:00-04:00",
      updated_at: "2024-01-01T12:05:00-04:00"
    }
  },

  // SendGrid Events
  sendgrid_email_delivered: {
    name: "SendGrid - Email Delivered",
    source: "sendgrid",
    payload: [
      {
        email: "example@test.com",
        timestamp: 1513299569,
        "smtp-id": "<14c5d75ce93.dfd.64b469@ismtpd-555>",
        event: "delivered",
        category: "cat facts",
        sg_event_id: "sendgrid_internal_event_id",
        sg_message_id: "sendgrid_internal_message_id"
      }
    ]
  },
  sendgrid_email_opened: {
    name: "SendGrid - Email Opened",
    source: "sendgrid",
    payload: [
      {
        email: "example@test.com",
        timestamp: 1513299569,
        "smtp-id": "<14c5d75ce93.dfd.64b469@ismtpd-555>",
        event: "open",
        category: "cat facts",
        sg_event_id: "sendgrid_internal_event_id",
        sg_message_id: "sendgrid_internal_message_id",
        useragent: "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322)",
        ip: "255.255.255.255"
      }
    ]
  },

  // Mailchimp Events
  mailchimp_subscribe: {
    name: "Mailchimp - User Subscribed",
    source: "mailchimp",
    payload: {
      type: "subscribe",
      fired_at: "2024-01-01 12:00:00",
      data: {
        id: "edc26d43eb",
        list_id: "a6b5da1054",
        email: "example@example.com",
        email_type: "html",
        merges: {
          EMAIL: "example@example.com",
          FNAME: "Example",
          LNAME: "User",
          INTERESTS: ""
        },
        ip_opt: "198.2.191.34",
        ip_signup: "198.2.191.34"
      }
    }
  },
  mailchimp_unsubscribe: {
    name: "Mailchimp - User Unsubscribed",
    source: "mailchimp",
    payload: {
      type: "unsubscribe",
      fired_at: "2024-01-01 12:00:00",
      data: {
        action: "unsub",
        reason: "manual",
        id: "edc26d43eb",
        list_id: "a6b5da1054",
        email: "example@example.com",
        email_type: "html",
        merges: {
          EMAIL: "example@example.com",
          FNAME: "Example",
          LNAME: "User",
          INTERESTS: ""
        },
        ip_opt: "198.2.191.34",
        campaign_id: "4e770e5903"
      }
    }
  },

  // Zoom Events
  zoom_meeting_started: {
    name: "Zoom - Meeting Started",
    source: "zoom",
    payload: {
      event: "meeting.started",
      payload: {
        account_id: "EAbFxvtTRqeOr_2WSY9zzg",
        object: {
          uuid: "4444AAAiAAAAAiAiAiiAii==",
          id: 1111111,
          host_id: "z8yBXeShTmSbmUosFax7Gg",
          topic: "My Meeting",
          type: 2,
          start_time: "2024-01-01T12:00:00Z",
          duration: 60,
          timezone: "America/Los_Angeles",
          agenda: "",
          created_at: "2024-01-01T11:00:00Z",
          join_url: "https://zoom.us/j/1111111?pwd=xxxxxxx"
        }
      },
      event_ts: 1640995200000
    }
  },
  zoom_meeting_ended: {
    name: "Zoom - Meeting Ended",
    source: "zoom",
    payload: {
      event: "meeting.ended",
      payload: {
        account_id: "EAbFxvtTRqeOr_2WSY9zzg",
        object: {
          uuid: "4444AAAiAAAAAiAiAiiAii==",
          id: 1111111,
          host_id: "z8yBXeShTmSbmUosFax7Gg",
          topic: "My Meeting",
          type: 2,
          start_time: "2024-01-01T12:00:00Z",
          end_time: "2024-01-01T13:00:00Z",
          duration: 60,
          timezone: "America/Los_Angeles"
        }
      },
      event_ts: 1640999200000
    }
  },

  // Webhooks.site Test Event
  webhooks_site_test: {
    name: "Webhooks.site - Test Event",
    source: "webhooks",
    payload: {
      message: "This is a test webhook payload",
      timestamp: "2024-01-01T12:00:00Z",
      event_type: "test",
      data: {
        user_id: "12345",
        action: "test_webhook",
        metadata: {
          source: "webhooks.site",
          version: "1.0"
        }
      }
    }
  },

  // Linear Events
  linear_issue_created: {
    name: "Linear - Issue Created",
    source: "linear",
    payload: {
      action: "create",
      data: {
        id: "issue-id-123",
        title: "Fix authentication bug",
        description: "Users are unable to login with Google OAuth",
        priority: 2,
        state: {
          id: "state-todo",
          name: "Todo",
          type: "triage"
        },
        team: {
          id: "team-123",
          name: "Engineering",
          key: "ENG"
        },
        assignee: {
          id: "user-123",
          name: "Alice Johnson",
          email: "alice@company.com"
        },
        creator: {
          id: "user-456",
          name: "Bob Smith",
          email: "bob@company.com"
        },
        createdAt: "2024-01-01T12:00:00.000Z",
        updatedAt: "2024-01-01T12:00:00.000Z",
        number: 42,
        identifier: "ENG-42",
        url: "https://linear.app/company/issue/ENG-42"
      },
      type: "Issue",
      organizationId: "org-123",
      webhookTimestamp: 1640995200000,
      webhookId: "webhook-123"
    }
  },

  // Notion Events
  notion_page_created: {
    name: "Notion - Page Created",
    source: "notion",
    payload: {
      object: "event",
      event_id: "event-123",
      event_type: "page.created",
      event_time: "2024-01-01T12:00:00.000Z",
      data: {
        object: "page",
        id: "page-123",
        created_time: "2024-01-01T12:00:00.000Z",
        last_edited_time: "2024-01-01T12:00:00.000Z",
        created_by: {
          object: "user",
          id: "user-123"
        },
        last_edited_by: {
          object: "user",
          id: "user-123"
        },
        cover: null,
        icon: null,
        parent: {
          type: "database_id",
          database_id: "database-123"
        },
        archived: false,
        properties: {
          "Name": {
            id: "title",
            type: "title",
            title: [
              {
                type: "text",
                text: {
                  content: "New Task",
                  link: null
                }
              }
            ]
          }
        },
        url: "https://www.notion.so/New-Task-page-123"
      }
    }
  },

  // HubSpot Events
  hubspot_contact_created: {
    name: "HubSpot - Contact Created",
    source: "hubspot",
    payload: {
      eventId: 123456789,
      subscriptionId: 12345,
      portalId: 62515,
      occurredAt: 1640995200000,
      subscriptionType: "contact.creation",
      attemptNumber: 0,
      objectId: 123,
      changeSource: "CRM_UI",
      objectType: "CONTACT",
      properties: {
        firstname: {
          value: "John",
          timestamp: 1640995200000,
          source: "API",
          sourceId: "userId:123"
        },
        lastname: {
          value: "Doe",
          timestamp: 1640995200000,
          source: "API",
          sourceId: "userId:123"
        },
        email: {
          value: "john.doe@example.com",
          timestamp: 1640995200000,
          source: "API",
          sourceId: "userId:123"
        }
      }
    }
  },

  // Salesforce Events
  salesforce_opportunity_created: {
    name: "Salesforce - Opportunity Created",
    source: "salesforce",
    payload: {
      organizationId: "00D000000000001",
      actionName: "OpportunityCreated",
      sObject: {
        attributes: {
          type: "Opportunity",
          url: "/services/data/v52.0/sobjects/Opportunity/006000000000001"
        },
        Id: "006000000000001",
        Name: "New Business Opportunity",
        StageName: "Prospecting",
        CloseDate: "2024-03-01",
        Amount: 50000,
        AccountId: "001000000000001",
        OwnerId: "005000000000001",
        CreatedDate: "2024-01-01T12:00:00.000+0000",
        LastModifiedDate: "2024-01-01T12:00:00.000+0000"
      }
    }
  },

  // Confluence Events
  confluence_page_created: {
    name: "Confluence - Page Created",
    source: "confluence",
    payload: {
      timestamp: 1642780800000,
      event: "page_created",
      user: {
        type: "known",
        profilePicture: {
          path: "/wiki/aa-avatar/557058:f8f53a95-66a1-4686-b772-54a21b199654",
          width: 48,
          height: 48,
          isDefault: false
        },
        displayName: "John Doe",
        operations: null,
        username: "jdoe",
        userKey: "557058:f8f53a95-66a1-4686-b772-54a21b199654",
        accountId: "557058:f8f53a95-66a1-4686-b772-54a21b199654"
      },
      page: {
        id: "1234567890",
        title: "New Documentation Page",
        status: "current",
        body: {
          storage: {
            value: "<p>This is a new documentation page created for the project.</p>",
            representation: "storage"
          }
        },
        space: {
          id: 123456,
          key: "DOCS",
          name: "Documentation",
          type: "global"
        },
        history: {
          latest: true,
          createdBy: {
            type: "known",
            displayName: "John Doe",
            username: "jdoe",
            userKey: "557058:f8f53a95-66a1-4686-b772-54a21b199654"
          },
          createdDate: "2024-01-01T12:00:00.000Z"
        },
        version: {
          by: {
            type: "known",
            displayName: "John Doe",
            username: "jdoe",
            userKey: "557058:f8f53a95-66a1-4686-b772-54a21b199654"
          },
          when: "2024-01-01T12:00:00.000Z",
          number: 1,
          minorEdit: false
        },
        ancestors: [],
        descendants: {
          page: {
            results: [],
            start: 0,
            limit: 25
          }
        }
      }
    }
  },
  confluence_page_updated: {
    name: "Confluence - Page Updated",
    source: "confluence",
    payload: {
      timestamp: 1642784400000,
      event: "page_updated",
      user: {
        type: "known",
        profilePicture: {
          path: "/wiki/aa-avatar/557058:f8f53a95-66a1-4686-b772-54a21b199654",
          width: 48,
          height: 48,
          isDefault: false
        },
        displayName: "Jane Smith",
        operations: null,
        username: "jsmith",
        userKey: "557058:a1b2c3d4-5e6f-7890-abcd-ef1234567890",
        accountId: "557058:a1b2c3d4-5e6f-7890-abcd-ef1234567890"
      },
      page: {
        id: "1234567890",
        title: "Updated Documentation Page",
        status: "current",
        body: {
          storage: {
            value: "<p>This documentation page has been updated with new information.</p><h2>New Section</h2><p>Additional content added.</p>",
            representation: "storage"
          }
        },
        space: {
          id: 123456,
          key: "DOCS",
          name: "Documentation",
          type: "global"
        },
        history: {
          latest: true,
          createdBy: {
            type: "known",
            displayName: "John Doe",
            username: "jdoe",
            userKey: "557058:f8f53a95-66a1-4686-b772-54a21b199654"
          },
          createdDate: "2024-01-01T12:00:00.000Z"
        },
        version: {
          by: {
            type: "known",
            displayName: "Jane Smith",
            username: "jsmith",
            userKey: "557058:a1b2c3d4-5e6f-7890-abcd-ef1234567890"
          },
          when: "2024-01-01T13:00:00.000Z",
          number: 2,
          minorEdit: false
        },
        ancestors: [],
        descendants: {
          page: {
            results: [],
            start: 0,
            limit: 25
          }
        }
      }
    }
  },
  confluence_comment_created: {
    name: "Confluence - Comment Created",
    source: "confluence",
    payload: {
      timestamp: 1642787000000,
      event: "comment_created",
      user: {
        type: "known",
        profilePicture: {
          path: "/wiki/aa-avatar/557058:c9d8e7f6-5432-1098-abcd-ef9876543210",
          width: 48,
          height: 48,
          isDefault: false
        },
        displayName: "Bob Wilson",
        operations: null,
        username: "bwilson",
        userKey: "557058:c9d8e7f6-5432-1098-abcd-ef9876543210",
        accountId: "557058:c9d8e7f6-5432-1098-abcd-ef9876543210"
      },
      comment: {
        id: "9876543210",
        title: "",
        type: "comment",
        status: "current",
        body: {
          storage: {
            value: "<p>Great documentation! This will be very helpful for the team.</p>",
            representation: "storage"
          }
        },
        container: {
          id: "1234567890",
          title: "Updated Documentation Page",
          type: "page"
        },
        version: {
          by: {
            type: "known",
            displayName: "Bob Wilson",
            username: "bwilson",
            userKey: "557058:c9d8e7f6-5432-1098-abcd-ef9876543210"
          },
          when: "2024-01-01T14:30:00.000Z",
          number: 1,
          minorEdit: false
        },
        ancestors: []
      }
    }
  },
  confluence_space_created: {
    name: "Confluence - Space Created",
    source: "confluence",
    payload: {
      timestamp: 1642690800000,
      event: "space_created",
      user: {
        type: "known",
        profilePicture: {
          path: "/wiki/aa-avatar/557058:admin123-456-789-abc-def123456789",
          width: 48,
          height: 48,
          isDefault: false
        },
        displayName: "Admin User",
        operations: null,
        username: "admin",
        userKey: "557058:admin123-456-789-abc-def123456789",
        accountId: "557058:admin123-456-789-abc-def123456789"
      },
      space: {
        id: 654321,
        key: "PROJ",
        name: "Project Alpha",
        type: "global",
        status: "current",
        description: {
          plain: {
            value: "Space for Project Alpha documentation and collaboration",
            representation: "plain"
          }
        },
        homepage: {
          id: "1111111111",
          title: "Project Alpha Home",
          type: "page"
        },
        metadata: {
          labels: {
            results: [
              {
                prefix: "global",
                name: "project",
                label: "project"
              },
              {
                prefix: "global",
                name: "alpha",
                label: "alpha"
              }
            ]
          }
        }
      }
    }
  }
};

export const payloadCategories = {
  "GitHub": [
    "github_pr_opened",
    "github_pr_merged", 
    "github_push",
    "github_issue_opened",
    "github_release_published"
  ],
  "Slack": [
    "slack_message",
    "slack_file_shared",
    "slack_user_joined",
    "slack_app_mention"
  ],
  "Atlassian Jira": [
    "jira_issue_created",
    "jira_issue_updated"
  ],
  "Atlassian Confluence": [
    "confluence_page_created",
    "confluence_page_updated",
    "confluence_comment_created",
    "confluence_space_created"
  ],
  "Twilio": [
    "twilio_sms_received",
    "twilio_call_completed"
  ],
  "Discord": [
    "discord_message_create",
    "discord_member_join"
  ],
  "Stripe": [
    "stripe_payment_succeeded",
    "stripe_customer_created", 
    "stripe_subscription_updated"
  ],
  "Shopify": [
    "shopify_order_created",
    "shopify_order_paid"
  ],
  "SendGrid": [
    "sendgrid_email_delivered",
    "sendgrid_email_opened"
  ],
  "Mailchimp": [
    "mailchimp_subscribe",
    "mailchimp_unsubscribe"
  ],
  "Zoom": [
    "zoom_meeting_started",
    "zoom_meeting_ended"
  ],
  "Linear": [
    "linear_issue_created"
  ],
  "Notion": [
    "notion_page_created"
  ],
  "HubSpot": [
    "hubspot_contact_created"
  ],
  "Salesforce": [
    "salesforce_opportunity_created"
  ],
  "Testing": [
    "webhooks_site_test"
  ]
};
